from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "train_data" / "1007-1030.xlsx"

IGNORED_SHEET_NAMES = {"Sheet1", "測試項目配方"}

COLUMN_ALIASES = {
    "測試異常項目\n(異常停止)": "異常項目\n(異常即停止)",
    "測試異常項目\n(全部測試)": "異常項目\n(異常續測)",
}

REQUIRED_COLUMNS = {
    "異常編號",
    "測試次數",
    "維修處置\n(先維修再測試)",
}

SOURCE_COLUMNS = ["來源檔案", "來源工作表", "原始異常編號"]


@dataclass
class SheetReport:
    file_name: str
    sheet_name: str
    status: str
    rows: int = 0
    reason: str = ""


@dataclass
class MergeResult:
    dataframe: pd.DataFrame
    sheet_reports: list[SheetReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def loaded_sheets(self) -> list[SheetReport]:
        return [report for report in self.sheet_reports if report.status == "loaded"]

    @property
    def skipped_sheets(self) -> list[SheetReport]:
        return [report for report in self.sheet_reports if report.status == "skipped"]

    def summary(self) -> dict[str, int]:
        duplicate_keys = 0
        if not self.dataframe.empty:
            key_columns = [col for col in ["異常編號", "測試次數", "序號"] if col in self.dataframe.columns]
            if key_columns:
                duplicate_keys = int(self.dataframe.duplicated(key_columns).sum())

        return {
            "loaded_sheets": len(self.loaded_sheets),
            "skipped_sheets": len(self.skipped_sheets),
            "output_rows": int(len(self.dataframe)),
            "output_columns": int(len(self.dataframe.columns)),
            "unique_cases": int(self.dataframe["異常編號"].replace("", pd.NA).nunique())
            if "異常編號" in self.dataframe
            else 0,
            "duplicate_case_rows": duplicate_keys,
        }


def merge_excel_sources(
    sources: Iterable[tuple[str, bytes | Path]],
    *,
    include_source_columns: bool = False,
    keep_extra_columns: bool = False,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
) -> MergeResult:
    template_columns = _load_template_columns(template_path)
    frames: list[pd.DataFrame] = []
    reports: list[SheetReport] = []
    warnings: list[str] = []

    for file_name, payload in sources:
        try:
            workbook = _open_workbook(payload)
        except Exception as exc:
            reports.append(SheetReport(file_name, "", "skipped", reason=f"無法讀取 Excel：{exc}"))
            continue

        for sheet_name in workbook.sheet_names:
            if _should_ignore_sheet(sheet_name):
                reports.append(SheetReport(file_name, sheet_name, "skipped", reason="非資料工作表"))
                continue

            try:
                frame = pd.read_excel(workbook, sheet_name=sheet_name, dtype=object)
            except Exception as exc:
                reports.append(SheetReport(file_name, sheet_name, "skipped", reason=f"讀取失敗：{exc}"))
                continue

            frame = _normalize_columns(frame.dropna(how="all"))
            reason = _validate_data_sheet(frame)
            if reason:
                reports.append(SheetReport(file_name, sheet_name, "skipped", rows=len(frame), reason=reason))
                continue

            original_ids = frame["異常編號"].map(_clean_excel_value)
            converted_ids = []
            for original_id in original_ids:
                if not original_id:
                    converted_ids.append(pd.NA)
                    continue

                converted_id, warning = build_unique_abnormal_id(original_id, file_name, sheet_name)
                converted_ids.append(converted_id)
                if warning:
                    warnings.append(warning)

            frame["異常編號"] = converted_ids

            if include_source_columns:
                frame["來源檔案"] = file_name
                frame["來源工作表"] = sheet_name
                frame["原始異常編號"] = original_ids

            frame = _align_to_template(
                frame,
                template_columns,
                include_source_columns=include_source_columns,
                keep_extra_columns=keep_extra_columns,
            )
            frames.append(frame)
            reports.append(SheetReport(file_name, sheet_name, "loaded", rows=len(frame)))

    if frames:
        merged = pd.concat(frames, ignore_index=True)
    else:
        merged_columns = template_columns + (SOURCE_COLUMNS if include_source_columns else [])
        merged = pd.DataFrame(columns=merged_columns)

    return MergeResult(dataframe=merged, sheet_reports=reports, warnings=_dedupe(warnings))


def build_unique_abnormal_id(original_id: Any, file_name: str, sheet_name: str) -> tuple[str, str | None]:
    original_text = _clean_excel_value(original_id)
    if not original_text:
        return "", None

    if re.match(r"^\d{4}-\d{2}-\d{2}(?:-.+)?$", original_text):
        return original_text, None

    match = re.match(r"^\s*(\d{1,2})(?:[-_](.+))?\s*$", original_text)
    if not match:
        return original_text, f"{file_name} / {sheet_name} 的異常編號「{original_text}」不是 day-index 格式，已保留原值"

    day = int(match.group(1))
    index_text = str(match.group(2) or "").strip()
    inferred_date = _infer_case_date(day, sheet_name, file_name)
    if inferred_date is None:
        return original_text, f"{file_name} / {sheet_name} 的異常編號「{original_text}」無法推回日期，已保留原值"

    if index_text:
        return f"{inferred_date:%Y-%m-%d}-{index_text}", None
    return f"{inferred_date:%Y-%m-%d}", None


def dataframe_to_excel_bytes(dataframe: pd.DataFrame, sheet_name: str = "工作表1") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer.getvalue()


def _open_workbook(payload: bytes | Path) -> pd.ExcelFile:
    if isinstance(payload, (bytes, bytearray)):
        return pd.ExcelFile(BytesIO(payload))
    return pd.ExcelFile(payload)


def _load_template_columns(template_path: Path) -> list[str]:
    if not template_path.exists():
        return []
    template = pd.read_excel(template_path, nrows=0)
    template = _normalize_columns(template)
    return [str(col) for col in template.columns if not _is_unnamed_column(col)]


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = frame.rename(columns=COLUMN_ALIASES)
    renamed = renamed.loc[:, [not _is_unnamed_column(col) for col in renamed.columns]]
    return _combine_duplicate_columns(renamed)


def _combine_duplicate_columns(frame: pd.DataFrame) -> pd.DataFrame:
    combined = pd.DataFrame(index=frame.index)
    for column in dict.fromkeys(frame.columns):
        same_name = frame.loc[:, frame.columns == column]
        if same_name.shape[1] == 1:
            combined[column] = same_name.iloc[:, 0]
        else:
            combined[column] = same_name.bfill(axis=1).iloc[:, 0]
    return combined


def _validate_data_sheet(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "空白工作表"

    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        return "缺少必要欄位：" + ", ".join(missing)

    test_columns = [column for column in frame.columns if str(column).startswith("M") and "測試結果" in str(column)]
    if not test_columns:
        return "找不到 M01-M12 測試結果欄位"

    if frame["異常編號"].dropna().empty:
        return "異常編號皆為空白"

    return ""


def _align_to_template(
    frame: pd.DataFrame,
    template_columns: list[str],
    *,
    include_source_columns: bool,
    keep_extra_columns: bool,
) -> pd.DataFrame:
    if template_columns:
        for column in template_columns:
            if column not in frame.columns:
                frame[column] = pd.NA

        columns = list(template_columns)
        if keep_extra_columns:
            columns.extend([column for column in frame.columns if column not in columns and column not in SOURCE_COLUMNS])
    else:
        columns = [column for column in frame.columns if column not in SOURCE_COLUMNS]

    if include_source_columns:
        columns.extend([column for column in SOURCE_COLUMNS if column in frame.columns])

    return frame.loc[:, columns]


def _should_ignore_sheet(sheet_name: str) -> bool:
    normalized = str(sheet_name).strip()
    return normalized in IGNORED_SHEET_NAMES or "測試項目配方" in normalized


def _is_unnamed_column(column: Any) -> bool:
    return str(column).startswith("Unnamed")


def _clean_excel_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _infer_case_date(day: int, *texts: str) -> date | None:
    for text in texts:
        ranges = _extract_date_ranges(text)
        for start, end in ranges:
            matching = _date_in_range_with_day(start, end, day)
            if matching is not None:
                return matching
        if ranges:
            return ranges[0][0]
    return None


def _extract_date_ranges(text: str) -> list[tuple[date, date]]:
    raw_dates = re.findall(r"(\d{8})", str(text))
    parsed_dates = [_parse_yyyymmdd(raw) for raw in raw_dates]
    parsed_dates = [value for value in parsed_dates if value is not None]
    if not parsed_dates:
        return []

    ranges = []
    for index in range(0, len(parsed_dates), 2):
        start = parsed_dates[index]
        end = parsed_dates[index + 1] if index + 1 < len(parsed_dates) else start
        if end < start:
            start, end = end, start
        ranges.append((start, end))
    return ranges


def _parse_yyyymmdd(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        return None


def _date_in_range_with_day(start: date, end: date, day: int) -> date | None:
    current = start
    while current <= end:
        if current.day == day:
            return current
        current += timedelta(days=1)
    return None


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
