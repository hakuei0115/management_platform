from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

from open_set_rf_prediction import (
    DEFAULT_MODEL_PATH,
    FEATURE_COL,
    TARGET_COL,
    OpenSetRfMcprPredictor,
    OpenSetThresholds,
)
from repair_normalization import normalize_repair_suggestion


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RULES_PATH = PROJECT_ROOT / "NG項_最終維修建議對照.csv"
GROUP_COL = "異常編號"


@dataclass
class TrainingResult:
    model_path: Path
    thresholds: OpenSetThresholds
    validation: dict[str, Any]
    metadata: dict[str, Any]


def train_open_set_rf_mcpr(
    rules: pd.DataFrame,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    n_estimators: int = 300,
    test_size: float = 0.2,
    random_state: int = 42,
    thresholds: OpenSetThresholds | None = None,
    auto_thresholds: bool = True,
    target_confident_accuracy: float = 0.75,
    min_confident_validation_rows: int = 5,
) -> TrainingResult:
    data = clean_rules(rules)
    validate_rules(data)
    thresholds = thresholds or OpenSetThresholds()

    split = make_eval_split(data, test_size=test_size, random_state=random_state)
    validation: dict[str, Any]
    threshold_source = "defaults"
    confident_prediction_enabled = True

    if split is not None:
        train_data = data.iloc[split["train_idx"]].reset_index(drop=True)
        eval_data = data.iloc[split["test_idx"]].reset_index(drop=True)
        eval_model, eval_encoder, eval_label_encoder = fit_rf_mcpr(
            train_data,
            label_source=data,
            n_estimators=n_estimators,
            random_state=random_state,
        )
        eval_bundle = build_open_set_bundle(
            model=eval_model,
            onehot_encoder=eval_encoder,
            label_encoder=eval_label_encoder,
            data=train_data,
            thresholds=thresholds,
            metadata={
                "model_name": "Open-set RF-MCPR calibration model",
                "split_strategy": split["strategy"],
            },
        )
        calibration_records = collect_validation_records(eval_bundle, eval_data)

        if auto_thresholds:
            calibrated, threshold_source, confident_prediction_enabled = calibrate_thresholds(
                calibration_records,
                thresholds,
                target_confident_accuracy=target_confident_accuracy,
                min_confident_validation_rows=min_confident_validation_rows,
            )
            if calibrated != thresholds:
                thresholds = calibrated
            eval_bundle["thresholds"] = thresholds.as_dict()
            eval_bundle["confident_prediction_enabled"] = confident_prediction_enabled

        validation = summarize_validation(eval_bundle, eval_data)
        validation["split_strategy"] = split["strategy"]
        validation["threshold_source"] = threshold_source
    else:
        validation = {
            "split_strategy": "not_enough_data",
            "threshold_source": threshold_source,
            "total_rows": 0,
        }

    final_model, final_encoder, final_label_encoder = fit_rf_mcpr(
        data,
        label_source=data,
        n_estimators=n_estimators,
        random_state=random_state,
    )
    metadata = {
        "schema_version": "open_set_rf_mcpr_v1",
        "model_name": "Open-set RF-MCPR",
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "training_rows": int(len(data)),
        "unique_ng_items": int(data[FEATURE_COL].nunique()),
        "unique_repairs": int(data[TARGET_COL].nunique()),
        "n_estimators": n_estimators,
        "test_size": test_size,
        "random_state": random_state,
        "threshold_source": threshold_source,
        "confident_prediction_enabled": confident_prediction_enabled,
    }
    final_bundle = build_open_set_bundle(
        model=final_model,
        onehot_encoder=final_encoder,
        label_encoder=final_label_encoder,
        data=data,
        thresholds=thresholds,
        metadata=metadata,
        validation=validation,
        confident_prediction_enabled=confident_prediction_enabled,
    )

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_bundle, model_path)
    return TrainingResult(
        model_path=model_path,
        thresholds=thresholds,
        validation=validation,
        metadata=metadata,
    )


def clean_rules(rules: pd.DataFrame) -> pd.DataFrame:
    missing = sorted({FEATURE_COL, TARGET_COL} - set(rules.columns))
    if missing:
        raise ValueError("缺少必要欄位：" + ", ".join(missing))

    data = rules.copy()
    data = data.dropna(subset=[FEATURE_COL, TARGET_COL])
    data[FEATURE_COL] = data[FEATURE_COL].astype(str).str.strip()
    data[TARGET_COL] = data[TARGET_COL].map(normalize_repair_suggestion)
    data = data[(data[FEATURE_COL] != "") & (data[TARGET_COL] != "")]
    return data.reset_index(drop=True)


def validate_rules(data: pd.DataFrame) -> None:
    if len(data) < 2:
        raise ValueError("可訓練資料少於 2 筆")
    if data[TARGET_COL].nunique() < 2:
        raise ValueError("維修建議類別少於 2 種，無法訓練分類模型")


def make_eval_split(data: pd.DataFrame, *, test_size: float, random_state: int) -> dict[str, Any] | None:
    if len(data) < 5:
        return None

    # 稀有類別保護 (Rare Class Protection):
    class_counts = data[TARGET_COL].value_counts()
    rare_classes = set(class_counts[class_counts <= 2].index)

    protected_train_indices = []
    evaluable_indices = []

    for cls in data[TARGET_COL].unique():
        cls_indices = data[data[TARGET_COL] == cls].index.tolist()
        if cls in rare_classes:
            protected_train_indices.append(cls_indices[0])
            evaluable_indices.extend(cls_indices[1:])
        else:
            evaluable_indices.extend(cls_indices)

    if not evaluable_indices:
        evaluable_indices = data.index.tolist()
        protected_train_indices = []

    sub_data = data.loc[evaluable_indices]

    if GROUP_COL in sub_data.columns and sub_data[GROUP_COL].nunique() >= 5:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        sub_train_pos, sub_test_pos = next(splitter.split(sub_data, groups=sub_data[GROUP_COL].astype(str)))
        train_idx = np.unique(np.concatenate([protected_train_indices, sub_data.index[sub_train_pos].to_numpy()]))
        test_idx = sub_data.index[sub_test_pos].to_numpy()
        strategy = "group_holdout_rare_protected"
    else:
        sub_class_counts = sub_data[TARGET_COL].value_counts()
        stratify = sub_data[TARGET_COL] if len(sub_class_counts) > 0 and sub_class_counts.min() >= 2 else None
        sub_train_idx, sub_test_idx = train_test_split(
            sub_data.index.to_numpy(),
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )
        train_idx = np.unique(np.concatenate([protected_train_indices, sub_train_idx]))
        test_idx = sub_test_idx
        strategy = "row_holdout_rare_protected"

    return {
        "train_idx": train_idx,
        "test_idx": test_idx,
        "strategy": strategy,
    }


def fit_rf_mcpr(
    data: pd.DataFrame,
    *,
    label_source: pd.DataFrame,
    n_estimators: int,
    random_state: int,
) -> tuple[RandomForestClassifier, OneHotEncoder, LabelEncoder]:
    onehot_encoder = OneHotEncoder(handle_unknown="ignore")
    label_encoder = LabelEncoder().fit(label_source[TARGET_COL])

    features = onehot_encoder.fit_transform(data[[FEATURE_COL]])
    target = label_encoder.transform(data[TARGET_COL])
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        class_weight="balanced_subsample",
    )
    model.fit(features, target)
    return model, onehot_encoder, label_encoder


def build_open_set_bundle(
    *,
    model: RandomForestClassifier,
    onehot_encoder: OneHotEncoder,
    label_encoder: LabelEncoder,
    data: pd.DataFrame,
    thresholds: OpenSetThresholds,
    metadata: dict[str, Any],
    validation: dict[str, Any] | None = None,
    confident_prediction_enabled: bool = True,
) -> dict[str, Any]:
    x_train = onehot_encoder.transform(data[[FEATURE_COL]])
    y_train = label_encoder.transform(data[TARGET_COL])
    train_leaves = model.apply(x_train).astype(np.int64)
    n_trees = len(model.estimators_)
    n_classes = len(label_encoder.classes_)

    leaf_counts_by_tree = [
        dict(Counter(int(value) for value in train_leaves[:, tree_index]))
        for tree_index in range(n_trees)
    ]

    class_leaf_counts_by_tree: dict[int, list[dict[int, int]]] = {}
    for class_id in range(n_classes):
        class_leaves = train_leaves[y_train == class_id]
        class_leaf_counts_by_tree[class_id] = [
            dict(Counter(int(value) for value in class_leaves[:, tree_index]))
            for tree_index in range(n_trees)
        ]

    ng_counts = {
        str(ng_key): int(count)
        for ng_key, count in data[FEATURE_COL].value_counts().items()
    }
    ng_repair_counts = {
        (str(ng_key), str(repair)): int(count)
        for (ng_key, repair), count in data.groupby([FEATURE_COL, TARGET_COL]).size().items()
    }

    return {
        "schema_version": "open_set_rf_mcpr_v1",
        "model": model,
        "onehot_encoder": onehot_encoder,
        "label_encoder": label_encoder,
        "feature_col": FEATURE_COL,
        "target_col": TARGET_COL,
        "thresholds": thresholds.as_dict(),
        "known_ng_items": sorted(str(value) for value in data[FEATURE_COL].unique()),
        "ng_counts": ng_counts,
        "ng_repair_counts": ng_repair_counts,
        "class_counts": np.bincount(y_train, minlength=n_classes),
        "leaf_counts_by_tree": leaf_counts_by_tree,
        "class_leaf_counts_by_tree": class_leaf_counts_by_tree,
        "train_leaves": train_leaves,
        "y_train": y_train,
        "metadata": metadata,
        "validation": validation or {},
        "confident_prediction_enabled": confident_prediction_enabled,
    }


def collect_validation_records(bundle: dict[str, Any], eval_data: pd.DataFrame, *, top_n: int = 5) -> pd.DataFrame:
    predictor = OpenSetRfMcprPredictor(bundle)
    records: list[dict[str, Any]] = []
    for _, row in eval_data.iterrows():
        report = predictor.predict(ng_key=str(row[FEATURE_COL]), top_n=top_n)
        candidates = report["candidates"]
        top_repair = candidates[0]["repair"] if candidates else None
        true_repair = str(row[TARGET_COL])
        records.append(
            {
                "ng_key": report["input"]["ng_key"],
                "known_ng_key": bool(report["input"]["known_ng_key"]),
                "true_repair": true_repair,
                "top_repair": top_repair,
                "top1_correct": bool(top_repair == true_repair),
                "topn_hit": bool(any(candidate["repair"] == true_repair for candidate in candidates)),
                "top_vote_ratio": report["diagnostics"]["top_vote_ratio"],
                "vote_margin": report["diagnostics"]["vote_margin"],
                "vote_entropy": report["diagnostics"]["vote_entropy"],
                "leaf_support_mean": report["diagnostics"]["leaf_support_mean"],
                "best_leaf_proximity": report["diagnostics"]["best_leaf_proximity"],
                "candidate_margin": report["diagnostics"]["candidate_margin"],
            }
        )
    return pd.DataFrame(records)


def calibrate_thresholds(
    records: pd.DataFrame,
    base: OpenSetThresholds,
    *,
    target_confident_accuracy: float,
    min_confident_validation_rows: int,
) -> tuple[OpenSetThresholds, str, bool]:
    if records.empty:
        return base, "defaults_no_validation", True

    candidate_thresholds = build_threshold_grid(records, base)
    best: tuple[int, float, OpenSetThresholds] | None = None
    for candidate in candidate_thresholds:
        confident = confident_mask(records, candidate)
        count = int(confident.sum())
        if count < min_confident_validation_rows:
            continue

        accuracy = float(records.loc[confident, "top1_correct"].mean())
        if accuracy < target_confident_accuracy:
            continue

        current = (count, accuracy, candidate)
        if best is None or current[0] > best[0] or (current[0] == best[0] and current[1] > best[1]):
            best = current

    if best is None:
        # The validation split did not prove any high-confidence region. Keep
        # useful candidates, but force them into reference_prediction instead
        # of confident_prediction.
        return base, "validation_no_reliable_confident_region", False

    return best[2], "validation_target_accuracy", True


def build_threshold_grid(records: pd.DataFrame, base: OpenSetThresholds) -> list[OpenSetThresholds]:
    vote_values = sorted(set([base.min_top_vote_ratio, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]))
    margin_values = sorted(set([base.min_vote_margin, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]))
    entropy_values = sorted(set([base.max_vote_entropy, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35]), reverse=True)
    candidate_margin_values = sorted(set([base.min_candidate_margin, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]))

    correct = records[records["top1_correct"]]
    if not correct.empty:
        vote_values.append(percentile(correct["top_vote_ratio"], 25))
        margin_values.append(percentile(correct["vote_margin"], 25))
        entropy_values.append(percentile(correct["vote_entropy"], 75))
        candidate_margin_values.append(percentile(correct["candidate_margin"], 25))

    thresholds = []
    for vote in sorted(set(vote_values)):
        for margin in sorted(set(margin_values)):
            for entropy in sorted(set(entropy_values), reverse=True):
                for candidate_margin in sorted(set(candidate_margin_values)):
                    thresholds.append(
                        OpenSetThresholds(
                            min_top_vote_ratio=float(vote),
                            min_vote_margin=float(margin),
                            max_vote_entropy=float(entropy),
                            min_leaf_support_mean=base.min_leaf_support_mean,
                            min_leaf_proximity=base.min_leaf_proximity,
                            min_candidate_margin=float(candidate_margin),
                        )
                    )
    return thresholds


def confident_mask(records: pd.DataFrame, thresholds: OpenSetThresholds) -> pd.Series:
    return (
        records["known_ng_key"].astype(bool)
        & (records["leaf_support_mean"] >= thresholds.min_leaf_support_mean)
        & (records["best_leaf_proximity"] >= thresholds.min_leaf_proximity)
        & (records["top_vote_ratio"] >= thresholds.min_top_vote_ratio)
        & (records["vote_margin"] >= thresholds.min_vote_margin)
        & (records["vote_entropy"] <= thresholds.max_vote_entropy)
        & (records["candidate_margin"] >= thresholds.min_candidate_margin)
    )


def summarize_validation(bundle: dict[str, Any], eval_data: pd.DataFrame, *, top_n: int = 5) -> dict[str, Any]:
    predictor = OpenSetRfMcprPredictor(bundle)
    rows: list[dict[str, Any]] = []
    for _, row in eval_data.iterrows():
        report = predictor.predict(ng_key=str(row[FEATURE_COL]), top_n=top_n)
        candidates = report["candidates"]
        output = report["decision"]["output"]
        true_repair = str(row[TARGET_COL])
        rows.append(
            {
                "status": report["decision"]["status"],
                "output": output,
                "true_repair": true_repair,
                "top_repair": candidates[0]["repair"] if candidates else None,
                "output_correct": bool(output == true_repair),
                "top1_correct": bool(candidates and candidates[0]["repair"] == true_repair),
                "topn_hit": bool(any(candidate["repair"] == true_repair for candidate in candidates)),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return {"total_rows": 0}

    non_unknown = frame[frame["status"] != "unknown"]
    confident = frame[frame["status"] == "confident_prediction"]
    reference = frame[frame["status"] == "reference_prediction"]
    unknown = frame[frame["status"] == "unknown"]

    return {
        "total_rows": int(len(frame)),
        "status_counts": {str(key): int(value) for key, value in frame["status"].value_counts().items()},
        "raw_top1_accuracy": mean_bool(frame["top1_correct"]),
        "raw_topn_hit_rate": mean_bool(frame["topn_hit"]),
        "non_unknown_coverage": round_float(len(non_unknown) / len(frame)),
        "non_unknown_output_accuracy": mean_bool(non_unknown["output_correct"]),
        "confident_count": int(len(confident)),
        "confident_accuracy": mean_bool(confident["output_correct"]),
        "reference_count": int(len(reference)),
        "reference_topn_hit_rate": mean_bool(reference["topn_hit"]),
        "unknown_count": int(len(unknown)),
    }


def percentile(series: pd.Series, q: float) -> float:
    return float(np.percentile(pd.to_numeric(series, errors="coerce").dropna(), q))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def mean_bool(series: pd.Series) -> float | None:
    if len(series) == 0:
        return None
    return round_float(float(series.astype(bool).mean()))


def round_float(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Open-set RF-MCPR bundle")
    parser.add_argument("--input", "-i", default=str(DEFAULT_RULES_PATH), help="NG rules CSV")
    parser.add_argument("--output", "-o", default=str(DEFAULT_MODEL_PATH), help="Output model bundle")
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--no-auto-thresholds", action="store_true")
    parser.add_argument("--target-confident-accuracy", type=float, default=0.75)
    parser.add_argument("--min-confident-validation-rows", type=int, default=5)
    parser.add_argument("--min-top-vote-ratio", type=float, default=OpenSetThresholds.min_top_vote_ratio)
    parser.add_argument("--min-vote-margin", type=float, default=OpenSetThresholds.min_vote_margin)
    parser.add_argument("--max-vote-entropy", type=float, default=OpenSetThresholds.max_vote_entropy)
    parser.add_argument("--min-leaf-support-mean", type=float, default=OpenSetThresholds.min_leaf_support_mean)
    parser.add_argument("--min-leaf-proximity", type=float, default=OpenSetThresholds.min_leaf_proximity)
    parser.add_argument("--min-candidate-margin", type=float, default=OpenSetThresholds.min_candidate_margin)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = OpenSetThresholds(
        min_top_vote_ratio=args.min_top_vote_ratio,
        min_vote_margin=args.min_vote_margin,
        max_vote_entropy=args.max_vote_entropy,
        min_leaf_support_mean=args.min_leaf_support_mean,
        min_leaf_proximity=args.min_leaf_proximity,
        min_candidate_margin=args.min_candidate_margin,
    )
    rules = pd.read_csv(args.input)
    result = train_open_set_rf_mcpr(
        rules,
        model_path=args.output,
        n_estimators=args.n_estimators,
        test_size=args.test_size,
        random_state=args.random_state,
        thresholds=thresholds,
        auto_thresholds=not args.no_auto_thresholds,
        target_confident_accuracy=args.target_confident_accuracy,
        min_confident_validation_rows=args.min_confident_validation_rows,
    )

    print(f"Model saved: {result.model_path}")
    print("Thresholds:")
    for key, value in result.thresholds.as_dict().items():
        print(f"  {key}: {value}")
    print("Validation:")
    for key, value in result.validation.items():
        print(f"  {key}: {value}")
    print(f"Confident prediction enabled: {result.metadata['confident_prediction_enabled']}")


if __name__ == "__main__":
    main()
