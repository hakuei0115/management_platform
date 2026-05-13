from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_INPUT_PATH = Path("train_data/1007-1030.xlsx")
DEFAULT_OUTPUT_PATH = Path("NG項_最終維修建議對照.csv")

ID_COL = "異常編號"
COUNT_COL = "測試次數"
REPAIR_COL = "維修處置\n(先維修再測試)"
NG_COL = "異常項目\n(異常續測)"

COLUMN_ALIASES = {
    "測試異常項目\n(異常停止)": "異常項目\n(異常即停止)",
    "測試異常項目\n(全部測試)": NG_COL,
}


@dataclass
class NgRuleStats:
    input_rows: int = 0
    abnormal_groups: int = 0
    groups_with_pass: int = 0
    groups_without_pass: int = 0
    groups_without_repair: int = 0
    groups_without_ng_before_pass: int = 0
    output_rows: int = 0
    unique_ng_items: int = 0
    unique_repairs: int = 0
    test_columns: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "input_rows": self.input_rows,
            "abnormal_groups": self.abnormal_groups,
            "groups_with_pass": self.groups_with_pass,
            "groups_without_pass": self.groups_without_pass,
            "groups_without_repair": self.groups_without_repair,
            "groups_without_ng_before_pass": self.groups_without_ng_before_pass,
            "output_rows": self.output_rows,
            "unique_ng_items": self.unique_ng_items,
            "unique_repairs": self.unique_repairs,
            "test_columns": self.test_columns,
        }


def load_training_excel(input_path: str | Path, sheet_name: str | None = None) -> pd.DataFrame:
    input_path = Path(input_path)
    if sheet_name:
        frame = pd.read_excel(input_path, sheet_name=sheet_name, dtype=object)
    else:
        workbook = pd.ExcelFile(input_path)
        frame = pd.read_excel(workbook, sheet_name=workbook.sheet_names[0], dtype=object)
    return normalize_columns(frame)


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(columns=COLUMN_ALIASES)
    renamed = renamed.loc[:, [not str(column).startswith("Unnamed") for column in renamed.columns]]
    return combine_duplicate_columns(renamed)


def combine_duplicate_columns(frame: pd.DataFrame) -> pd.DataFrame:
    combined = pd.DataFrame(index=frame.index)
    for column in dict.fromkeys(frame.columns):
        same_name = frame.loc[:, frame.columns == column]
        if same_name.shape[1] == 1:
            combined[column] = same_name.iloc[:, 0]
        else:
            combined[column] = same_name.bfill(axis=1).iloc[:, 0]
    return combined


def generate_ng_rules(frame: pd.DataFrame) -> tuple[pd.DataFrame, NgRuleStats]:
    frame = normalize_columns(frame.dropna(how="all"))
    validate_input_frame(frame)

    test_cols = [column for column in frame.columns if str(column).startswith("M") and "測試結果" in str(column)]
    stats = NgRuleStats(
        input_rows=len(frame),
        abnormal_groups=int(frame[ID_COL].dropna().nunique()),
        test_columns=len(test_cols),
    )

    records: list[dict[str, Any]] = []
    grouped = frame[frame[ID_COL].notna()].groupby(ID_COL, sort=False)
    for abnormal_id, group in grouped:
        group = sort_group_by_test_count(group).reset_index(drop=True)

        pass_rows = group[group[NG_COL].map(is_pass_value)]
        if pass_rows.empty:
            stats.groups_without_pass += 1
            continue
        stats.groups_with_pass += 1

        pass_idx = int(pass_rows.index[-1])
        final_repair = group.loc[pass_idx, REPAIR_COL]
        if pd.isna(final_repair) or str(final_repair).strip() == "":
            stats.groups_without_repair += 1
            continue

        group_records = []
        for index in range(pass_idx):
            row = group.loc[index, test_cols]
            ng_tests = [
                column.replace("_測試結果", "")
                for column, value in row.items()
                if is_ng_value(value)
            ]
            if not ng_tests:
                continue

            group_records.append(
                {
                    "異常編號": abnormal_id,
                    "NG項": ", ".join(sorted(ng_tests)),
                    "維修建議": str(final_repair).strip(),
                }
            )

        if group_records:
            records.extend(group_records)
        else:
            stats.groups_without_ng_before_pass += 1

    output = pd.DataFrame(records, columns=["異常編號", "NG項", "維修建議"])
    stats.output_rows = len(output)
    stats.unique_ng_items = int(output["NG項"].nunique()) if not output.empty else 0
    stats.unique_repairs = int(output["維修建議"].nunique()) if not output.empty else 0
    return output, stats


def write_ng_rules(
    input_path: str | Path,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, NgRuleStats]:
    frame = load_training_excel(input_path, sheet_name=sheet_name)
    output, stats = generate_ng_rules(frame)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output, stats


def validate_input_frame(frame: pd.DataFrame) -> None:
    required = {ID_COL, NG_COL, REPAIR_COL}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("缺少必要欄位：" + ", ".join(missing))

    test_cols = [column for column in frame.columns if str(column).startswith("M") and "測試結果" in str(column)]
    if not test_cols:
        raise ValueError("找不到 M01-M12 測試結果欄位")


def sort_group_by_test_count(group: pd.DataFrame) -> pd.DataFrame:
    if COUNT_COL not in group.columns:
        return group

    sortable = group.copy()
    sortable["_sort_count"] = pd.to_numeric(sortable[COUNT_COL], errors="coerce")
    sortable["_sort_order"] = range(len(sortable))
    return sortable.sort_values(["_sort_count", "_sort_order"], kind="stable").drop(
        columns=["_sort_count", "_sort_order"]
    )


def is_pass_value(value: Any) -> bool:
    if pd.isna(value):
        return False
    return "PASS" in str(value).replace(" ", "").upper()


def is_ng_value(value: Any) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().upper().endswith("NG")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生 NG項_最終維修建議對照.csv")
    parser.add_argument("--input", "-i", default=str(DEFAULT_INPUT_PATH), help="輸入 Excel 路徑")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT_PATH), help="輸出 CSV 路徑")
    parser.add_argument("--sheet", "-s", default=None, help="指定工作表名稱，未指定時讀取第一個工作表")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output, stats = write_ng_rules(args.input, args.output, sheet_name=args.sheet)

    print(f"📋 偵測到 {stats.test_columns} 個測試結果欄")
    print("\n📊 NG→最終維修建議 對照表（前10筆）：")
    print(output.head(10))
    print("\n📈 統計：")
    for key, value in stats.as_dict().items():
        print(f"  {key}: {value}")
    print(f"\n✅ 已輸出：{args.output}")


if __name__ == "__main__":
    main()
