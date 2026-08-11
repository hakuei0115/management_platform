from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from admdp_dataset import (
    PASS_STATE,
    AdmdpDatasetConfig,
    get_test_columns,
    load_transition_excel,
    make_decision_state,
    normalize_columns,
)
from admdp_training import DEFAULT_POLICY_PATH


def load_admdp_model(model_path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    return joblib.load(model_path)


def recommend_from_state(
    state: str,
    *,
    model: dict[str, Any] | None = None,
    model_path: str | Path = DEFAULT_POLICY_PATH,
    top_n: int = 5,
) -> dict[str, Any]:
    if model is None:
        model = load_admdp_model(model_path)

    q_table = model["q_table"]
    exact = q_table[q_table["state"] == state].sort_values(["q_value", "visits"], ascending=[False, False])
    if not exact.empty:
        return {
            "state": state,
            "matched": True,
            "best_action": exact.iloc[0]["action"],
            "alternatives": exact.head(top_n).to_dict("records"),
            "reason": "ADMDP exact state match",
        }

    fallback = fallback_actions(q_table, state, top_n=top_n)
    return {
        "state": state,
        "matched": False,
        "best_action": fallback[0]["action"] if fallback else None,
        "alternatives": fallback,
        "reason": "state not found; using global action value fallback",
    }


def recommend_from_rows(
    previous_row: pd.Series | dict[str, Any] | None,
    current_row: pd.Series | dict[str, Any],
    *,
    model: dict[str, Any] | None = None,
    model_path: str | Path = DEFAULT_POLICY_PATH,
    test_cols: list[str] | None = None,
    leak_threshold: float = 0.0,
    top_n: int = 5,
) -> dict[str, Any]:
    current_series = to_series(current_row)
    previous_series = to_series(previous_row) if previous_row is not None else None

    frame = pd.DataFrame([current_series])
    if previous_series is not None:
        frame = pd.DataFrame([previous_series, current_series])
    frame = normalize_columns(frame)

    current_series = frame.iloc[-1]
    previous_series = frame.iloc[-2] if len(frame) > 1 else None
    if test_cols is None:
        test_cols = get_test_columns(frame)

    state = make_decision_state(
        current_series,
        previous_series,
        test_cols,
        leak_threshold=leak_threshold,
    )
    result = recommend_from_state(state, model=model, model_path=model_path, top_n=top_n)
    result["state"] = state
    return result


def fallback_actions(q_table: pd.DataFrame, state: str, *, top_n: int) -> list[dict[str, Any]]:
    if q_table.empty:
        return []

    # Keep a tiny bit of domain awareness: if the current state has ng=...,
    # prefer actions that have been valuable in states with the same NG signature.
    ng_prefix = extract_state_part(state, "ng")
    scoped = q_table
    if ng_prefix:
        same_ng = q_table[q_table["state"].str.contains(f"ng={ng_prefix}", regex=False)]
        if not same_ng.empty:
            scoped = same_ng

    fallback = (
        scoped.groupby("action", as_index=False)
        .agg(
            q_value=("q_value", "mean"),
            visits=("visits", "sum"),
            avg_immediate_reward=("avg_immediate_reward", "mean"),
            absorbing_probability=("absorbing_probability", "mean"),
        )
        .sort_values(["q_value", "visits"], ascending=[False, False])
        .head(top_n)
    )
    return fallback.to_dict("records")


def extract_state_part(state: str, key: str) -> str:
    prefix = f"{key}="
    for part in state.split(" | "):
        if part.startswith(prefix):
            return part[len(prefix) :]
    return ""


def to_series(row: pd.Series | dict[str, Any]) -> pd.Series:
    if isinstance(row, pd.Series):
        return row
    return pd.Series(row)


def explain_recommendation(result: dict[str, Any]) -> str:
    best_action = result.get("best_action")
    if not best_action:
        return "ADMDP 找不到可用建議"
    if result.get("matched"):
        return f"ADMDP 建議「{best_action}」，因為目前 state 有歷史轉移資料。"
    return f"ADMDP 建議「{best_action}」，但目前 state 未出現過，使用相近/全域 action value 回退。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="查詢 ADMDP policy")
    parser.add_argument("--model", default=str(DEFAULT_POLICY_PATH), help="ADMDP policy pkl 路徑")
    parser.add_argument("--state", help="直接指定 ADMDP state")
    parser.add_argument("--excel", help="用合併後 Excel 的某個 case/row 建立 state")
    parser.add_argument("--case-id", help="Excel 中的異常編號")
    parser.add_argument("--row-index", type=int, default=-1, help="case 內第幾筆 row，預設最後一筆")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--leak-threshold", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_admdp_model(args.model)

    if args.state:
        result = recommend_from_state(args.state, model=model, top_n=args.top_n)
    elif args.excel and args.case_id:
        frame = load_transition_excel(args.excel)
        case = frame[frame["異常編號"].astype(str) == str(args.case_id)].reset_index(drop=True)
        if case.empty:
            raise ValueError(f"找不到異常編號：{args.case_id}")
        row_index = args.row_index if args.row_index >= 0 else len(case) - 1
        if row_index >= len(case):
            raise ValueError(f"row-index 超出 case 長度：{row_index}")
        previous_row = case.loc[row_index - 1] if row_index > 0 else None
        current_row = case.loc[row_index]
        result = recommend_from_rows(
            previous_row,
            current_row,
            model=model,
            leak_threshold=args.leak_threshold,
            top_n=args.top_n,
        )
    else:
        raise ValueError("請提供 --state，或提供 --excel 與 --case-id")

    print("ADMDP recommendation:")
    print(f"  state: {result['state']}")
    print(f"  matched: {result['matched']}")
    print(f"  best_action: {result['best_action']}")
    print(f"  reason: {result['reason']}")
    print("\nAlternatives:")
    print(pd.DataFrame(result["alternatives"]))
    print("\n" + explain_recommendation(result))


if __name__ == "__main__":
    main()
