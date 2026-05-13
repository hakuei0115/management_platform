import joblib
import pandas as pd
import logging
import traceback
import os
from datetime import datetime
from pathlib import Path
from threading import Lock
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MODEL_VERSION = "v1.0.0"
MODEL_PATH = Path(os.environ.get("MODEL_PATH", "model/rf_mcpr.pkl"))
TRAINING_DATA_PATH = Path(os.environ.get("TRAINING_DATA_PATH", "data/NG項_最終維修建議對照.csv"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# 模型載入
# =========================
rf = None
ohe = None
le = None
df_train = pd.DataFrame()
_model_mtime = None
_data_mtime = None
_asset_lock = Lock()


def read_training_csv(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise ValueError(f"CSV 編碼無法辨識：{last_error}")


def load_assets(force=False):
    global rf, ohe, le, df_train, _model_mtime, _data_mtime, MODEL_VERSION

    with _asset_lock:
        model_mtime = MODEL_PATH.stat().st_mtime
        if force or _model_mtime != model_mtime:
            bundle = joblib.load(MODEL_PATH)
            rf = bundle["model"]
            ohe = bundle["onehot_encoder"]
            le = bundle["label_encoder"]
            metadata = bundle.get("metadata", {})
            MODEL_VERSION = metadata.get("trained_at", MODEL_VERSION)
            _model_mtime = model_mtime
            logging.info(f"模型載入成功：{MODEL_PATH}")

        if TRAINING_DATA_PATH.exists():
            data_mtime = TRAINING_DATA_PATH.stat().st_mtime
            if force or _data_mtime != data_mtime:
                df_train = read_training_csv(TRAINING_DATA_PATH)
                _data_mtime = data_mtime
                logging.info(f"訓練資料載入成功：{TRAINING_DATA_PATH}")
        else:
            df_train = pd.DataFrame()
            _data_mtime = None
            logging.warning(f"找不到訓練資料 CSV：{TRAINING_DATA_PATH}")


try:
    load_assets(force=True)
except Exception as e:
    logging.error(f"模型載入失敗: {str(e)}")
    raise e


# =========================
# NG 測試項目映射表
# =========================
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
    "m12": "M12_測試完成調壓"
}


# =========================
# 維修建議解析器
# =========================
def parse_repair_suggestion(text):
    if not isinstance(text, str) or text.strip() == "":
        return {"action": None, "part": None, "category": None}

    text = text.strip()

    # A. 動詞開頭 → action 類
    actions = ["更換", "吹淨", "清潔", "調整", "潤滑", "緊固"]
    for act in actions:
        if text.startswith(act):
            return {
                "action": act,
                "part": text[len(act):].strip(),
                "category": "action"
            }

    # C. 系統型異常（不算維修部位）
    system_keywords = ["B機", "系統", "程式", "停止", "偵測", "壓力", "NG"]
    if any(word in text for word in system_keywords):
        return {"action": None, "part": text, "category": "system"}

    # B. 其他 → 故障部位（也不算維修部位）
    return {"action": None, "part": text, "category": "fault"}


# =========================
# 單一 NG 項預測（完整機率）
# =========================
def predict_single_ng(ng_full, n=5):
    try:
        X_sample = ohe.transform(pd.DataFrame({"NG項": [ng_full]}))
        probs = rf.predict_proba(X_sample)[0]

        df_prob = pd.DataFrame({
            "suggestion": le.classes_,
            "probability": probs
        }).sort_values("probability", ascending=False)

        results = []
        for _, row in df_prob.head(n).iterrows():
            parsed = parse_repair_suggestion(row["suggestion"])
            results.append({
                "suggestion": row["suggestion"],
                "probability": float(row["probability"]),
                "action": parsed["action"],
                "part": parsed["part"],
                "category": parsed["category"]
            })

        return results

    except Exception as e:
        logging.error(f"predict_single_ng 錯誤: {str(e)}")
        return []


# =========================
# API Route
# =========================
@app.route("/predict", methods=["POST"])
def predict():
    try:
        load_assets()
        data = request.get_json()
        ng_items = data.get("ng_items", [])
        top_n = data.get("top_n", 5)

        # === 0. 無 NG 項 ===
        if not ng_items:
            resp = {
                "suggestions": "產品狀態良好，無須維修",
                "parts": []
            }
            return jsonify({"success": True, "data": resp})

        # === 1. NG 簡碼 → 全名 ===
        translated = []
        for ng in ng_items:
            key = ng.lower()
            if key not in TEST_COLUMNS:
                return jsonify({"success": False, "error": f"未知 NG 項目：{ng}"}), 400
            translated.append(TEST_COLUMNS[key])

        # === 2. 逐一 NG 預測 ===
        all_predictions = []
        for ng_full in translated:
            all_predictions.extend(predict_single_ng(ng_full, top_n))

        # === 3. 合併結果後排序 ===
        df_all = pd.DataFrame(all_predictions).sort_values(
            "probability", ascending=False
        ).reset_index(drop=True)

        # === 4. 合併建議字串 ===
        merged_suggestions_str = ", ".join(
            [f"{row['suggestion']}({row['probability']:.2f})" for _, row in df_all.iterrows()]
        )

        # === 5. 可能維修部位（只取 action 類） ===
        likely_parts = []
        for _, row in df_all.iterrows():
            if row["category"] == "action":  # 只加入「動詞類建議」
                part = row["part"]
                if part and part not in likely_parts:
                    likely_parts.append(part)

        # === 6. 回傳資料 ===
        response_data = {
            "suggestions": merged_suggestions_str,
            "parts": likely_parts
        }

        # Log
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "model_version": MODEL_VERSION,
            "input_ng_items": ng_items,
            "translated_items": translated,
            "outputs": response_data
        }

        pd.DataFrame([log_record]).to_csv(
            LOG_DIR / "prediction_history.csv",
            mode="a",
            index=False,
            header=False
        )

        logging.info(f"預測成功: {log_record}")

        return jsonify({"success": True, "data": response_data})

    except Exception as e:
        error_msg = traceback.format_exc()
        logging.error(error_msg)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_msg
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("MODEL_PREDICT_PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
