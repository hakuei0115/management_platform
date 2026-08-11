from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from admdp_prediction import load_admdp_model, recommend_from_state


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RF_MODEL_PATH = PROJECT_ROOT / "model" / "rf_mcpr.pkl"
DEFAULT_ADMDP_MODEL_PATH = PROJECT_ROOT / "model" / "admdp_policy.pkl"
DEFAULT_RULES_PATH = PROJECT_ROOT / "NG項_最終維修建議對照.csv"


def predict_two_stage(
    ng_key: str,
    *,
    admdp_state: str | None = None,
    rf_model_path: str | Path = DEFAULT_RF_MODEL_PATH,
    admdp_model_path: str | Path = DEFAULT_ADMDP_MODEL_PATH,
    rules_path: str | Path = DEFAULT_RULES_PATH,
    top_n: int = 5,
) -> dict[str, Any]:
    rf_predictions = predict_rf_mcpr_topn(
        ng_key,
        model_path=rf_model_path,
        rules_path=rules_path,
        top_n=top_n,
    )

    admdp_prediction = None
    if admdp_state:
        admdp_model = load_admdp_model(admdp_model_path)
        admdp_prediction = recommend_from_state(admdp_state, model=admdp_model, top_n=top_n)

    return {
        "ng_key": ng_key,
        "rf_mcpr": rf_predictions,
        "admdp": admdp_prediction,
        "final_suggestion": choose_final_suggestion(rf_predictions, admdp_prediction),
    }


def predict_rf_mcpr_topn(
    ng_key: str,
    *,
    model_path: str | Path = DEFAULT_RF_MODEL_PATH,
    rules_path: str | Path = DEFAULT_RULES_PATH,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    bundle = joblib.load(model_path)
    model = bundle["model"]
    onehot_encoder = bundle["onehot_encoder"]
    label_encoder = bundle["label_encoder"]

    features = onehot_encoder.transform(pd.DataFrame({"NG項": [ng_key]}))
    probabilities = model.predict_proba(features)[0]
    predictions = pd.DataFrame(
        {
            "suggestion": label_encoder.classes_,
            "probability": probabilities,
        }
    )

    valid_suggestions = valid_suggestions_for_ng(ng_key, rules_path)
    if valid_suggestions:
        predictions = predictions[predictions["suggestion"].isin(valid_suggestions)]

    predictions = predictions.sort_values("probability", ascending=False).head(top_n)
    return [
        {
            "suggestion": row["suggestion"],
            "probability": float(row["probability"]),
        }
        for _, row in predictions.iterrows()
    ]


def valid_suggestions_for_ng(ng_key: str, rules_path: str | Path) -> set[str]:
    rules_path = Path(rules_path)
    if not rules_path.exists():
        return set()
    rules = pd.read_csv(rules_path)
    if "NG項" not in rules.columns or "維修建議" not in rules.columns:
        return set()
    return set(rules.loc[rules["NG項"] == ng_key, "維修建議"].dropna().astype(str))


def choose_final_suggestion(
    rf_predictions: list[dict[str, Any]],
    admdp_prediction: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if admdp_prediction and admdp_prediction.get("best_action"):
        return {
            "source": "ADMDP",
            "suggestion": admdp_prediction["best_action"],
            "reason": admdp_prediction["reason"],
        }
    if rf_predictions:
        return {
            "source": "RF-MCPR",
            "suggestion": rf_predictions[0]["suggestion"],
            "reason": "no ADMDP state supplied",
        }
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RF-MCPR + ADMDP 二階段預測")
    parser.add_argument("--ng-key", required=True, help="NG 項組合，例如 M11_高壓氣密測試")
    parser.add_argument("--admdp-state", default=None, help="目前 ADMDP state；未提供時只回 RF-MCPR")
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = predict_two_stage(args.ng_key, admdp_state=args.admdp_state, top_n=args.top_n)
    print("Two-stage prediction:")
    print(f"  ng_key: {result['ng_key']}")
    print(f"  final: {result['final_suggestion']}")
    print("\nRF-MCPR:")
    print(pd.DataFrame(result["rf_mcpr"]))
    if result["admdp"]:
        print("\nADMDP:")
        print(result["admdp"])


if __name__ == "__main__":
    main()
