from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "model" / "open_set_rf_mcpr.pkl"

FEATURE_COL = "NG項"
TARGET_COL = "維修建議"

TEST_COLUMNS = {
    "m01": "M01_低壓手動排水閥測試",
    "m02": "M02_高壓手動排水閥測試",
    "m03": "M03_低壓內漏調壓",
    "m04": "M04_低壓內漏測試",
    "m05": "M05_高壓內漏測試",
    "m06": "M06_低壓氣密調壓",
    "m07": "M07_低壓錶孔測試",
    "m08": "M08_低壓氣密測試",
    "m09": "M09_高壓氣密調壓",
    "m10": "M10_高壓錶孔測試",
    "m11": "M11_高壓氣密測試",
    "m12": "M12_測試完成調壓",
}


@dataclass(frozen=True)
class OpenSetThresholds:
    min_top_vote_ratio: float = 0.45
    min_vote_margin: float = 0.10
    max_vote_entropy: float = 0.75
    min_leaf_support_mean: float = 3.0
    min_leaf_proximity: float = 0.05
    min_candidate_margin: float = 0.03

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None) -> "OpenSetThresholds":
        if not values:
            return cls()
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        return cls(**{key: values[key] for key in allowed if key in values})

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


class OpenSetRfMcprPredictor:
    def __init__(self, bundle: dict[str, Any]) -> None:
        required = {
            "model",
            "onehot_encoder",
            "label_encoder",
            "thresholds",
            "known_ng_items",
            "ng_counts",
            "ng_repair_counts",
            "class_counts",
            "leaf_counts_by_tree",
            "class_leaf_counts_by_tree",
            "train_leaves",
            "y_train",
        }
        missing = sorted(required - set(bundle))
        if missing:
            raise ValueError("open-set bundle 缺少欄位：" + ", ".join(missing))

        self.bundle = bundle
        self.model = bundle["model"]
        self.onehot_encoder = bundle["onehot_encoder"]
        self.label_encoder = bundle["label_encoder"]
        self.thresholds = OpenSetThresholds.from_mapping(bundle.get("thresholds"))
        self.metadata = bundle.get("metadata", {})
        self.confident_prediction_enabled = bool(
            bundle.get(
                "confident_prediction_enabled",
                self.metadata.get("confident_prediction_enabled", True),
            )
        )

        self.known_ng_items = set(bundle["known_ng_items"])
        self.ng_counts = dict(bundle["ng_counts"])
        self.ng_repair_counts = dict(bundle["ng_repair_counts"])
        self.class_counts = np.asarray(bundle["class_counts"], dtype=int)
        self.leaf_counts_by_tree = bundle["leaf_counts_by_tree"]
        self.class_leaf_counts_by_tree = bundle["class_leaf_counts_by_tree"]
        self.train_leaves = np.asarray(bundle["train_leaves"], dtype=np.int64)
        self.y_train = np.asarray(bundle["y_train"], dtype=np.int64)

        self.class_labels = list(self.label_encoder.classes_)
        self.n_classes = len(self.class_labels)
        self.n_trees = len(self.model.estimators_)
        self.n_train = int(len(self.y_train))

    @classmethod
    def from_path(cls, model_path: str | Path = DEFAULT_MODEL_PATH) -> "OpenSetRfMcprPredictor":
        return cls(joblib.load(model_path))

    def predict(
        self,
        *,
        ng_items: list[str] | None = None,
        ng_key: str | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        resolved_ng_key = normalize_ng_key(ng_items=ng_items, ng_key=ng_key)
        sample = pd.DataFrame({FEATURE_COL: [resolved_ng_key]})
        x_sample = self.onehot_encoder.transform(sample)
        leaf_path = self.model.apply(x_sample).astype(np.int64)[0]

        rf_probability = self._predict_probability_by_class(x_sample)
        vote_stats = self._vote_stats(x_sample)
        local_density = self._local_density(leaf_path)
        candidates = self._score_candidates(
            ng_key=resolved_ng_key,
            leaf_path=leaf_path,
            rf_probability=rf_probability,
            vote_ratio_by_class=vote_stats["vote_ratio_by_class"],
        )
        candidates.sort(key=lambda item: item["final_confidence"], reverse=True)
        top_candidates = candidates[:top_n]

        best_leaf_proximity = max(
            (item["leaf_proximity"] for item in top_candidates),
            default=0.0,
        )
        candidate_margin = candidate_score_margin(top_candidates)
        known_ng = resolved_ng_key in self.known_ng_items
        seen_ng_support = int(self.ng_counts.get(resolved_ng_key, 0))

        open_set_reasons = self._open_set_reasons(
            known_ng=known_ng,
            local_density=local_density,
            best_leaf_proximity=best_leaf_proximity,
        )
        low_confidence_reasons = self._low_confidence_reasons(
            vote_stats=vote_stats,
            candidate_margin=candidate_margin,
        )
        decision = self._decision(
            top_candidates=top_candidates,
            open_set_reasons=open_set_reasons,
            low_confidence_reasons=low_confidence_reasons,
        )

        return {
            "input": {
                "ng_key": resolved_ng_key,
                "known_ng_key": known_ng,
                "seen_ng_support": seen_ng_support,
            },
            "decision": decision,
            "diagnostics": {
                "top_vote_label": vote_stats["top_vote_label"],
                "top_vote_ratio": vote_stats["top_vote_ratio"],
                "second_vote_ratio": vote_stats["second_vote_ratio"],
                "vote_margin": vote_stats["vote_margin"],
                "vote_entropy": vote_stats["vote_entropy"],
                "leaf_support_mean": local_density["leaf_support_mean"],
                "leaf_support_median": local_density["leaf_support_median"],
                "leaf_support_min": local_density["leaf_support_min"],
                "leaf_support_p10": local_density["leaf_support_p10"],
                "local_density": local_density["local_density"],
                "best_leaf_proximity": round_float(best_leaf_proximity),
                "candidate_margin": round_float(candidate_margin),
            },
            "candidates": top_candidates,
            "model_metadata": self.metadata,
            "thresholds": self.thresholds.as_dict(),
            "confident_prediction_enabled": self.confident_prediction_enabled,
        }

    def _predict_probability_by_class(self, x_sample: Any) -> dict[int, float]:
        probabilities = self.model.predict_proba(x_sample)[0]
        return {
            int(class_id): float(probabilities[index])
            for index, class_id in enumerate(self.model.classes_)
        }

    def _vote_stats(self, x_sample: Any) -> dict[str, Any]:
        tree_predictions = np.array(
            [int(estimator.predict(x_sample)[0]) for estimator in self.model.estimators_],
            dtype=np.int64,
        )
        vote_counts = Counter(tree_predictions)
        vote_ratio_by_class = {
            class_id: vote_counts.get(class_id, 0) / self.n_trees
            for class_id in range(self.n_classes)
        }
        ranked_votes = sorted(vote_ratio_by_class.items(), key=lambda item: item[1], reverse=True)
        top_class_id, top_vote_ratio = ranked_votes[0]
        second_vote_ratio = ranked_votes[1][1] if len(ranked_votes) > 1 else 0.0

        return {
            "vote_ratio_by_class": vote_ratio_by_class,
            "top_vote_label": self.class_labels[top_class_id],
            "top_vote_ratio": round_float(top_vote_ratio),
            "second_vote_ratio": round_float(second_vote_ratio),
            "vote_margin": round_float(top_vote_ratio - second_vote_ratio),
            "vote_entropy": round_float(normalized_entropy(list(vote_ratio_by_class.values()))),
        }

    def _local_density(self, leaf_path: np.ndarray) -> dict[str, float]:
        supports = np.array(
            [
                self.leaf_counts_by_tree[tree_index].get(int(leaf_id), 0)
                for tree_index, leaf_id in enumerate(leaf_path)
            ],
            dtype=float,
        )
        return {
            "leaf_support_mean": round_float(float(np.mean(supports))),
            "leaf_support_median": round_float(float(np.median(supports))),
            "leaf_support_min": round_float(float(np.min(supports))),
            "leaf_support_p10": round_float(float(np.percentile(supports, 10))),
            "local_density": round_float(float(np.mean(supports / max(self.n_train, 1)))),
        }

    def _score_candidates(
        self,
        *,
        ng_key: str,
        leaf_path: np.ndarray,
        rf_probability: dict[int, float],
        vote_ratio_by_class: dict[int, float],
    ) -> list[dict[str, Any]]:
        same_ng_total = int(self.ng_counts.get(ng_key, 0))
        nearest_train_by_class = self._nearest_train_proximity_by_class(leaf_path)
        candidates: list[dict[str, Any]] = []

        for class_id, label in enumerate(self.class_labels):
            class_support = int(self.class_counts[class_id])
            raw_leaf_proximity, class_leaf_support_mean = self._class_leaf_prototype(
                class_id=class_id,
                leaf_path=leaf_path,
            )
            prototype_reliability = class_support / (class_support + 5) if class_support else 0.0
            leaf_proximity = raw_leaf_proximity * prototype_reliability
            same_ng_support = int(self.ng_repair_counts.get((ng_key, label), 0))
            same_ng_prior = same_ng_support / same_ng_total if same_ng_total else 0.0
            final_confidence = (
                0.40 * rf_probability.get(class_id, 0.0)
                + 0.25 * vote_ratio_by_class.get(class_id, 0.0)
                + 0.25 * leaf_proximity
                + 0.10 * same_ng_prior
            )

            candidates.append(
                {
                    "repair": label,
                    "final_confidence": round_float(final_confidence),
                    "rf_probability": round_float(rf_probability.get(class_id, 0.0)),
                    "vote_ratio": round_float(vote_ratio_by_class.get(class_id, 0.0)),
                    "leaf_proximity": round_float(leaf_proximity),
                    "leaf_proximity_raw": round_float(raw_leaf_proximity),
                    "prototype_reliability": round_float(prototype_reliability),
                    "nearest_train_proximity": round_float(nearest_train_by_class.get(class_id, 0.0)),
                    "class_leaf_support_mean": round_float(class_leaf_support_mean),
                    "class_training_support": class_support,
                    "same_ng_support": same_ng_support,
                    "same_ng_prior": round_float(same_ng_prior),
                    "seen_for_same_ng": bool(same_ng_support),
                }
            )

        return candidates

    def _class_leaf_prototype(self, *, class_id: int, leaf_path: np.ndarray) -> tuple[float, float]:
        class_support = int(self.class_counts[class_id])
        if class_support == 0:
            return 0.0, 0.0

        class_tree_counts = self.class_leaf_counts_by_tree[class_id]
        raw_supports = np.array(
            [
                class_tree_counts[tree_index].get(int(leaf_id), 0)
                for tree_index, leaf_id in enumerate(leaf_path)
            ],
            dtype=float,
        )
        return float(np.mean(raw_supports / class_support)), float(np.mean(raw_supports))

    def _nearest_train_proximity_by_class(self, leaf_path: np.ndarray) -> dict[int, float]:
        sample_similarity = np.mean(self.train_leaves == leaf_path, axis=1)
        result: dict[int, float] = {}
        for class_id in range(self.n_classes):
            class_scores = sample_similarity[self.y_train == class_id]
            result[class_id] = float(np.max(class_scores)) if len(class_scores) else 0.0
        return result

    def _open_set_reasons(
        self,
        *,
        known_ng: bool,
        local_density: dict[str, float],
        best_leaf_proximity: float,
    ) -> list[str]:
        reasons: list[str] = []
        if not known_ng:
            reasons.append("ng_key_not_seen_in_training")
        if local_density["leaf_support_mean"] < self.thresholds.min_leaf_support_mean:
            reasons.append("low_leaf_support")
        if best_leaf_proximity < self.thresholds.min_leaf_proximity:
            reasons.append("low_leaf_prototype_similarity")
        return reasons

    def _low_confidence_reasons(
        self,
        *,
        vote_stats: dict[str, Any],
        candidate_margin: float,
    ) -> list[str]:
        reasons: list[str] = []
        if vote_stats["top_vote_ratio"] < self.thresholds.min_top_vote_ratio:
            reasons.append("low_tree_consensus")
        if vote_stats["vote_margin"] < self.thresholds.min_vote_margin:
            reasons.append("small_top1_top2_vote_margin")
        if vote_stats["vote_entropy"] > self.thresholds.max_vote_entropy:
            reasons.append("high_vote_entropy")
        if candidate_margin < self.thresholds.min_candidate_margin:
            reasons.append("small_top1_top2_candidate_margin")
        return reasons

    def _decision(
        self,
        *,
        top_candidates: list[dict[str, Any]],
        open_set_reasons: list[str],
        low_confidence_reasons: list[str],
    ) -> dict[str, Any]:
        if not top_candidates:
            open_set_reasons = open_set_reasons + ["no_candidate"]

        predicted_repair = top_candidates[0]["repair"] if top_candidates else None
        if open_set_reasons:
            status = "unknown"
            output = "UNKNOWN"
            confidence_level = "none"
            recommendation_mode = "no_recommendation"
        elif low_confidence_reasons:
            status = "reference_prediction"
            output = predicted_repair
            confidence_level = "low"
            recommendation_mode = "reference_only"
        elif not self.confident_prediction_enabled:
            status = "reference_prediction"
            output = predicted_repair
            confidence_level = "low"
            recommendation_mode = "reference_only"
            low_confidence_reasons = ["confident_prediction_disabled_by_validation"]
        else:
            status = "confident_prediction"
            output = predicted_repair
            confidence_level = "high"
            recommendation_mode = "actionable"

        return {
            "status": status,
            "output": output,
            "predicted_repair": predicted_repair,
            "confidence_level": confidence_level,
            "recommendation_mode": recommendation_mode,
            "is_open_set": bool(open_set_reasons),
            "open_set_reasons": open_set_reasons,
            "low_confidence_reasons": low_confidence_reasons,
            "reasons": open_set_reasons + low_confidence_reasons,
        }


def normalize_ng_key(
    *,
    ng_items: list[str] | None = None,
    ng_key: str | None = None,
) -> str:
    if ng_key:
        return ", ".join(part.strip() for part in ng_key.split(",") if part.strip())
    if not ng_items:
        raise ValueError("請提供 --ng 或 --ng-key")

    translated = []
    for item in ng_items:
        key = item.strip()
        translated.append(TEST_COLUMNS.get(key.lower(), key))
    return ", ".join(sorted(translated))


def normalized_entropy(probabilities: list[float]) -> float:
    non_zero = [prob for prob in probabilities if prob > 0]
    if len(non_zero) <= 1:
        return 0.0
    entropy = -sum(prob * math.log(prob) for prob in non_zero)
    max_entropy = math.log(len(probabilities))
    return entropy / max_entropy if max_entropy else 0.0


def candidate_score_margin(candidates: list[dict[str, Any]]) -> float:
    if len(candidates) < 2:
        return 1.0 if candidates else 0.0
    return float(candidates[0]["final_confidence"] - candidates[1]["final_confidence"])


def round_float(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def print_report(report: dict[str, Any]) -> None:
    input_info = report["input"]
    decision = report["decision"]
    diagnostics = report["diagnostics"]

    print(f"NG key: {input_info['ng_key']}")
    print(f"Known NG: {input_info['known_ng_key']} / support={input_info['seen_ng_support']}")
    print(
        "Decision:"
        f" {decision['status']} / output={decision['output']}"
        f" / confidence={decision['confidence_level']}"
        f" / mode={decision['recommendation_mode']}"
    )
    if decision["reasons"]:
        print("Reasons: " + ", ".join(decision["reasons"]))

    print("\nDiagnostics")
    print(
        "  vote:"
        f" top={diagnostics['top_vote_label']}"
        f" ratio={diagnostics['top_vote_ratio']}"
        f" margin={diagnostics['vote_margin']}"
        f" entropy={diagnostics['vote_entropy']}"
    )
    print(
        "  leaf:"
        f" support_mean={diagnostics['leaf_support_mean']}"
        f" support_p10={diagnostics['leaf_support_p10']}"
        f" best_proximity={diagnostics['best_leaf_proximity']}"
    )
    print(f"  candidate_margin: {diagnostics['candidate_margin']}")

    print("\nCandidates")
    for index, item in enumerate(report["candidates"], start=1):
        print(
            f"{index}. {item['repair']}"
            f" | final={item['final_confidence']}"
            f" | proba={item['rf_probability']}"
            f" | vote={item['vote_ratio']}"
            f" | leaf={item['leaf_proximity']}"
            f" | support={item['class_leaf_support_mean']}"
            f" | same_ng={item['same_ng_support']}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open-set RF-MCPR prediction")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--ng", nargs="+", default=["m08", "m11"], help="NG 項目代碼或完整名稱")
    parser.add_argument("--ng-key", help="直接指定已合併的 NG key")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    predictor = OpenSetRfMcprPredictor.from_path(args.model_path)
    report = predictor.predict(
        ng_items=args.ng if not args.ng_key else None,
        ng_key=args.ng_key,
        top_n=args.top_n,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
