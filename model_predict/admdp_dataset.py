from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from generate_ng_rules import (
    COUNT_COL,
    ID_COL,
    NG_COL,
    REPAIR_COL,
    is_ng_value,
    is_pass_value,
    load_training_excel,
    normalize_columns,
    sort_group_by_test_count,
)


LEAK_COLUMNS = [
    "M04_低壓內漏測試_洩漏量",
    "M05_高壓內漏測試_洩漏量",
    "M08_低壓氣密測試_洩漏量",
    "M11_高壓氣密測試_洩漏量",
]

SOURCE_FILE_COL = "來源檔案"
SOURCE_SHEET_COL = "來源工作表"
NO_ACTION = "NO_ACTION"
NO_NG = "NO_NG"
PASS_STATE = "PASS"


@dataclass
class AdmdpDatasetConfig:
    leak_threshold: float = 0.0
    pass_reward: float = 10.0
    improved_reward: float = 2.0
    same_reward: float = -0.5
    worse_reward: float = -3.0
    still_ng_penalty: float = -1.0
    no_signal_penalty: float = -0.5
    step_penalty: float = 0.2


@dataclass
class TransitionBuildResult:
    transitions: pd.DataFrame
    summary: dict[str, int | float]


def load_transition_excel(input_path: str | Path, sheet_name: str | None = None) -> pd.DataFrame:
    return load_training_excel(input_path, sheet_name=sheet_name)


def build_admdp_transitions(
    frame: pd.DataFrame,
    *,
    config: AdmdpDatasetConfig | None = None,
) -> TransitionBuildResult:
    config = config or AdmdpDatasetConfig()
    frame = normalize_columns(frame.dropna(how="all"))
    validate_transition_frame(frame)

    test_cols = get_test_columns(frame)
    records: list[dict[str, Any]] = []
    skipped_no_action = 0
    groups_with_rows = 0

    grouped = frame[frame[ID_COL].notna()].groupby(ID_COL, sort=False)
    for case_id, group in grouped:
        group = sort_group_by_test_count(group).reset_index(drop=True)
        if len(group) < 2:
            continue
        groups_with_rows += 1

        for index in range(len(group) - 1):
            current_row = group.loc[index]
            next_row = group.loc[index + 1]

            if is_pass_row(current_row):
                continue

            action = clean_action(next_row.get(REPAIR_COL))
            if action == NO_ACTION:
                skipped_no_action += 1
                continue

            previous_row = group.loc[index - 1] if index > 0 else None
            state_before = make_decision_state(current_row, previous_row, test_cols, config.leak_threshold)
            state_after = make_decision_state(next_row, current_row, test_cols, config.leak_threshold)
            leak_summary = summarize_leak_delta(current_row, next_row, config.leak_threshold)
            next_is_pass = is_pass_row(next_row)
            reward = compute_reward(leak_summary, next_is_pass=next_is_pass, config=config)

            records.append(
                {
                    "case_id": case_id,
                    "step_before": clean_excel_value(current_row.get(COUNT_COL)),
                    "step_after": clean_excel_value(next_row.get(COUNT_COL)),
                    "state_before": state_before,
                    "action": action,
                    "state_after": state_after,
                    "reward": reward,
                    "is_absorbing": bool(next_is_pass),
                    "ng_before": ng_signature(current_row, test_cols),
                    "ng_after": ng_signature(next_row, test_cols),
                    "prev_action": clean_action(current_row.get(REPAIR_COL)),
                    "leak_trend": leak_summary["overall_trend"],
                    "valid_leak_count": leak_summary["valid_count"],
                    "improved_count": leak_summary["improved_count"],
                    "same_count": leak_summary["same_count"],
                    "worse_count": leak_summary["worse_count"],
                    SOURCE_FILE_COL: current_row.get(SOURCE_FILE_COL, ""),
                    SOURCE_SHEET_COL: current_row.get(SOURCE_SHEET_COL, ""),
                    **leak_summary["delta_columns"],
                    **leak_summary["trend_columns"],
                }
            )

    transitions = pd.DataFrame(records)
    summary = {
        "input_rows": int(len(frame)),
        "abnormal_groups": int(frame[ID_COL].dropna().nunique()),
        "groups_with_transitions": int(groups_with_rows),
        "test_columns": int(len(test_cols)),
        "leak_columns": int(len([col for col in LEAK_COLUMNS if col in frame.columns])),
        "transition_rows": int(len(transitions)),
        "unique_states": int(pd.concat([transitions["state_before"], transitions["state_after"]]).nunique())
        if not transitions.empty
        else 0,
        "unique_actions": int(transitions["action"].nunique()) if not transitions.empty else 0,
        "absorbing_transitions": int(transitions["is_absorbing"].sum()) if not transitions.empty else 0,
        "skipped_no_action": int(skipped_no_action),
        "avg_reward": float(transitions["reward"].mean()) if not transitions.empty else 0.0,
    }
    return TransitionBuildResult(transitions=transitions, summary=summary)


def write_admdp_transitions(
    input_path: str | Path,
    output_path: str | Path,
    *,
    sheet_name: str | None = None,
    config: AdmdpDatasetConfig | None = None,
) -> TransitionBuildResult:
    frame = load_transition_excel(input_path, sheet_name=sheet_name)
    result = build_admdp_transitions(frame, config=config)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.transitions.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def validate_transition_frame(frame: pd.DataFrame) -> None:
    required = {ID_COL, REPAIR_COL}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("缺少必要欄位：" + ", ".join(missing))

    if not get_test_columns(frame):
        raise ValueError("找不到 M01-M12 測試結果欄位")

    if not any(column in frame.columns for column in LEAK_COLUMNS):
        raise ValueError("找不到 M04/M05/M08/M11 洩漏量欄位")


def get_test_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if str(column).startswith("M") and "測試結果" in str(column)]


def make_decision_state(
    row: pd.Series,
    previous_row: pd.Series | None,
    test_cols: list[str],
    leak_threshold: float,
) -> str:
    if is_pass_row(row):
        return PASS_STATE

    trend = "initial"
    if previous_row is not None:
        trend = summarize_leak_delta(previous_row, row, leak_threshold)["overall_trend"]

    return " | ".join(
        [
            f"ng={ng_signature(row, test_cols)}",
            f"trend={trend}",
            f"prev={clean_action(row.get(REPAIR_COL))}",
        ]
    )


def summarize_leak_delta(before_row: pd.Series, after_row: pd.Series, leak_threshold: float) -> dict[str, Any]:
    improved_count = 0
    same_count = 0
    worse_count = 0
    valid_count = 0
    delta_columns: dict[str, float | None] = {}
    trend_columns: dict[str, str] = {}

    for column in LEAK_COLUMNS:
        short_name = column.split("_", 1)[0]
        before_value = to_number(before_row.get(column))
        after_value = to_number(after_row.get(column))

        delta_key = f"{short_name}_delta"
        trend_key = f"{short_name}_trend"
        if before_value is None or after_value is None:
            delta_columns[delta_key] = None
            trend_columns[trend_key] = "missing"
            continue

        delta = after_value - before_value
        trend = classify_delta(delta, leak_threshold)
        delta_columns[delta_key] = float(delta)
        trend_columns[trend_key] = trend
        valid_count += 1

        if trend == "improved":
            improved_count += 1
        elif trend == "same":
            same_count += 1
        elif trend == "worse":
            worse_count += 1

    if valid_count == 0:
        overall_trend = "unknown"
    elif worse_count > improved_count:
        overall_trend = "worse"
    elif improved_count > worse_count:
        overall_trend = "improved"
    elif same_count > 0:
        overall_trend = "same"
    else:
        overall_trend = "mixed"

    return {
        "overall_trend": overall_trend,
        "valid_count": valid_count,
        "improved_count": improved_count,
        "same_count": same_count,
        "worse_count": worse_count,
        "delta_columns": delta_columns,
        "trend_columns": trend_columns,
    }


def compute_reward(
    leak_summary: dict[str, Any],
    *,
    next_is_pass: bool,
    config: AdmdpDatasetConfig,
) -> float:
    reward = -config.step_penalty
    if next_is_pass:
        reward += config.pass_reward
    else:
        reward += config.still_ng_penalty

    reward += leak_summary["improved_count"] * config.improved_reward
    reward += leak_summary["same_count"] * config.same_reward
    reward += leak_summary["worse_count"] * config.worse_reward

    if leak_summary["valid_count"] == 0 and not next_is_pass:
        reward += config.no_signal_penalty

    return float(reward)


def is_pass_row(row: pd.Series) -> bool:
    if NG_COL in row.index and is_pass_value(row.get(NG_COL)):
        return True
    return False


def ng_signature(row: pd.Series, test_cols: list[str]) -> str:
    if is_pass_row(row):
        return PASS_STATE

    ng_items = sorted(column.replace("_測試結果", "") for column in test_cols if is_ng_value(row.get(column)))
    if not ng_items:
        return NO_NG
    return ", ".join(ng_items)


def classify_delta(delta: float, leak_threshold: float) -> str:
    if delta < -abs(leak_threshold):
        return "improved"
    if delta > abs(leak_threshold):
        return "worse"
    return "same"


def clean_action(value: Any) -> str:
    text = clean_excel_value(value)
    return text if text else NO_ACTION


def clean_excel_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def to_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    number = pd.to_numeric(text, errors="coerce")
    if pd.isna(number):
        return None
    return float(number)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="建立 ADMDP 維修轉移資料集")
    parser.add_argument("--input", "-i", required=True, help="合併後訓練 Excel 路徑")
    parser.add_argument("--output", "-o", default="outputs/admdp_transitions.csv", help="輸出 transition CSV 路徑")
    parser.add_argument("--sheet", "-s", default=None, help="指定工作表，未指定時讀第一個工作表")
    parser.add_argument("--leak-threshold", type=float, default=0.0, help="洩漏量變化門檻")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AdmdpDatasetConfig(leak_threshold=args.leak_threshold)
    result = write_admdp_transitions(args.input, args.output, sheet_name=args.sheet, config=config)

    print("ADMDP transition dataset summary:")
    for key, value in result.summary.items():
        print(f"  {key}: {value}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
