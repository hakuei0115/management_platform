from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

import pandas as pd

from admdp_dataset import build_admdp_transitions
from admdp_training import train_admdp_policy
from excel_merge_pipeline import merge_excel_sources
from generate_ng_rules import generate_ng_rules
from open_set_rf_training import train_open_set_rf_mcpr
from rf_mcpr_training import train_rf_mcpr

PROJECT_ROOT = Path(__file__).resolve().parent
ROW_DATA_DIR = PROJECT_ROOT / "row_data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CACHE_FILE = OUTPUT_DIR / "historical_evaluation_cache.json"
CHECKPOINTS_DIR = OUTPUT_DIR / "checkpoints"


@dataclass
class HistoricalEvaluationStage:
    stage: int
    period_label: str
    stage_title: str
    file_count: int
    row_count: int
    rule_count: int
    unique_ng: int
    unique_repairs: int
    rf_accuracy: float
    rf_top3_accuracy: float
    rf_oob_score: float
    rf_f1: float
    rf_precision: float
    rf_recall: float
    open_set_accuracy: float
    open_set_coverage: float
    admdp_transitions: int
    admdp_states: int
    badge: str = ""
    is_latest: bool = False
    is_best_f1: bool = False


def extract_date_from_filename(filename: str) -> str:
    """從檔名提取年月資訊，如 D20251007... -> 2025-10"""
    match = re.search(r"D(\d{4})(\d{2})", filename)
    if match:
        year, month = match.group(1), match.group(2)
        return f"{year}-{month}"
    match_digits = re.search(r"(\d{4})(\d{2})", filename)
    if match_digits:
        year, month = match_digits.group(1), match_digits.group(2)
        return f"{year}-{month}"
    return "9999-99"


def group_row_data_files() -> list[tuple[str, list[Path]]]:
    """掃描 row_data 目錄，並按年月分組與時間排序"""
    if not ROW_DATA_DIR.exists():
        return []

    files = [f for f in ROW_DATA_DIR.glob("*.xlsx") if not f.name.startswith("~")]
    
    # 依日期排序
    sorted_files = sorted(files, key=lambda f: (extract_date_from_filename(f.name), f.name))

    grouped: dict[str, list[Path]] = {}
    for f in sorted_files:
        month_key = extract_date_from_filename(f.name)
        grouped.setdefault(month_key, []).append(f)

    # 回傳 [(month_key, [file1, file2...]), ...]
    return sorted(grouped.items(), key=lambda item: item[0])


def evaluate_historical_models(force_recompute: bool = False) -> list[dict[str, Any]]:
    """依累計時間視窗評估歷代模型表現，並快取結果"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not force_recompute and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print("⚠️ 讀取歷代模型評估快取失敗，重新計算:", e)

    grouped_months = group_row_data_files()
    if not grouped_months:
        return []

    cumulative_files: list[Path] = []
    stages: list[HistoricalEvaluationStage] = []

    best_f1_val = -1.0
    best_f1_idx = -1

    first_month = grouped_months[0][0]

    for idx, (month_key, month_files) in enumerate(grouped_months, start=1):
        cumulative_files.extend(month_files)

        if idx == 1:
            period_label = f"{month_key} (初始)"
            stage_title = f"{month_key} 初始模型"
        else:
            period_label = f"{first_month} ~ {month_key}"
            stage_title = f"{first_month} 至 {month_key} 累計模型"

        sources = [(f.name, f.read_bytes()) for f in cumulative_files]
        merge_res = merge_excel_sources(sources)

        if merge_res.dataframe.empty:
            continue

        raw_df = merge_res.dataframe
        row_count = int(len(raw_df))

        # 產生 NG 對照表
        try:
            rules, rule_stats = generate_ng_rules(raw_df)
        except Exception as err:
            print(f"⚠️ 階段 {idx} 產生 NG 對照表失敗:", err)
            continue

        rule_count = int(len(rules))
        unique_ng = int(rules["NG項"].nunique()) if "NG項" in rules else 0
        unique_repairs = int(rules["維修建議"].nunique()) if "維修建議" in rules else 0

        rf_acc, rf_top3_acc, rf_oob, rf_f1, rf_prec, rf_rec = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        open_set_acc, open_set_cov = 0.0, 0.0
        admdp_trans_cnt, admdp_states_cnt = 0, 0

        # 建立此階段模型檔庫歸檔目錄
        stage_dir = CHECKPOINTS_DIR / f"stage_{idx}"
        stage_dir.mkdir(parents=True, exist_ok=True)

        try:
            rules.to_csv(stage_dir / "NG項_最終維修建議對照.csv", index=False, encoding="utf-8-sig")
        except Exception as err:
            print(f"⚠️ 階段 {idx} 保存對照表失敗:", err)

        # 訓練 RF-MCPR 評估並歸檔 checkpoint
        try:
            rf_res = train_rf_mcpr(rules, model_path=stage_dir / "rf_mcpr.pkl", n_estimators=100)
            rf_acc = float(rf_res.metrics.get("accuracy", 0.0) or 0.0)
            rf_top3_acc = float(rf_res.metrics.get("top3_accuracy", 0.0) or 0.0)
            rf_oob = float(rf_res.metrics.get("oob_score", 0.0) or 0.0)
            rf_f1 = float(rf_res.metrics.get("f1", 0.0) or 0.0)
            rf_prec = float(rf_res.metrics.get("precision", 0.0) or 0.0)
            rf_rec = float(rf_res.metrics.get("recall", 0.0) or 0.0)
        except Exception as err:
            print(f"⚠️ 階段 {idx} RF-MCPR 評估失敗:", err)

        # 訓練 Open-Set 評估並歸檔 checkpoint
        try:
            os_res = train_open_set_rf_mcpr(rules, model_path=stage_dir / "open_set_rf.pkl", n_estimators=100)
            open_set_acc = float(os_res.validation.get("confident_accuracy", 0.0) or os_res.validation.get("raw_top1_accuracy", 0.0) or 0.0)
            open_set_cov = float(os_res.validation.get("non_unknown_coverage", 0.0) or 0.0)
        except Exception as err:
            print(f"⚠️ 階段 {idx} Open-Set 評估失敗:", err)

        # ADMDP 轉移鏈評估與歸檔 checkpoint
        try:
            admdp_res = build_admdp_transitions(raw_df)
            admdp_trans_cnt = int(len(admdp_res.transitions))
            if "curr_state" in admdp_res.transitions:
                admdp_states_cnt = int(admdp_res.transitions["curr_state"].nunique())
            admdp_res.transitions.to_csv(stage_dir / "admdp_state_transitions.csv", index=False, encoding="utf-8-sig")
            train_admdp_policy(admdp_res.transitions, model_path=stage_dir / "admdp_policy.pkl")
        except Exception as err:
            print(f"⚠️ 階段 {idx} ADMDP 轉移鏈評估與歸檔失敗:", err)

        eval_score = max(rf_f1, rf_acc, rf_top3_acc, open_set_acc)
        if eval_score > best_f1_val:
            best_f1_val = eval_score
            best_f1_idx = len(stages)

        stage_item = HistoricalEvaluationStage(
            stage=idx,
            period_label=period_label,
            stage_title=stage_title,
            file_count=len(cumulative_files),
            row_count=row_count,
            rule_count=rule_count,
            unique_ng=unique_ng,
            unique_repairs=unique_repairs,
            rf_accuracy=round(rf_acc, 4),
            rf_top3_accuracy=round(rf_top3_acc, 4),
            rf_oob_score=round(rf_oob, 4),
            rf_f1=round(rf_f1, 4),
            rf_precision=round(rf_prec, 4),
            rf_recall=round(rf_rec, 4),
            open_set_accuracy=round(open_set_accuracy_val(open_set_acc), 4),
            open_set_coverage=round(open_set_cov, 4),
            admdp_transitions=admdp_trans_cnt,
            admdp_states=admdp_states_cnt,
        )
        stages.append(stage_item)

    # 標註最新與最佳模型
    dict_results = [asdict(s) for s in stages]
    if dict_results:
        # 1. 標註最新版本
        dict_results[-1]["is_latest"] = True
        dict_results[-1]["badge"] = "現場運行"

        # 2. 找出綜合表現最佳版本 (極值 max score)
        best_idx = max(
            range(len(dict_results)),
            key=lambda i: max(dict_results[i]["rf_accuracy"], dict_results[i]["open_set_accuracy"], dict_results[i]["rf_f1"])
        )
        dict_results[best_idx]["is_best_f1"] = True
        if not dict_results[best_idx]["badge"]:
            dict_results[best_idx]["badge"] = "最高準率"
        elif "最高準率" not in dict_results[best_idx]["badge"]:
            dict_results[best_idx]["badge"] += " 最高準率"

        # 3. 初始對照版本
        if not dict_results[0]["badge"]:
            dict_results[0]["badge"] = "初始對照"

    # 存檔至 Cache
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(dict_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ 寫入歷代模型評估快取失敗:", e)

    return dict_results


def open_set_accuracy_val(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


if __name__ == "__main__":
    print("⚡ 正在評估歷代 AI 模型表現...")
    results = evaluate_historical_models(force_recompute=True)
    print(f"✅ 完成！共評估 {len(results)} 個歷代模型階段：")
    for r in results:
        print(f" - [{r['period_label']}] 樣本:{r['rule_count']}筆, RF-F1:{r['rf_f1']*100:.1f}%, OpenSet-Acc:{r['open_set_accuracy']*100:.1f}%, 標籤:{r['badge']}")
