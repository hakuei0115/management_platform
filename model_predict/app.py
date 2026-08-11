from __future__ import annotations
import joblib
import pandas as pd
import numpy as np
import logging
import traceback
import os
import json
import redis
from datetime import datetime
from pathlib import Path
from threading import Lock
from flask import Flask, request, jsonify
from flask_cors import CORS

from open_set_rf_prediction import OpenSetRfMcprPredictor
from admdp_prediction import load_admdp_model, recommend_from_state
from repair_normalization import normalize_repair_suggestion

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MODEL_VERSION = "v2.0.0"
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "model"))
RF_MODEL_PATH = MODEL_DIR / "rf_mcpr.pkl"
OPEN_SET_MODEL_PATH = MODEL_DIR / "open_set_rf_mcpr.pkl"
ADMDP_MODEL_PATH = MODEL_DIR / "admdp_policy.pkl"
TRAINING_DATA_PATH = Path(os.environ.get("TRAINING_DATA_PATH", "data/NG項_最終維修建議對照.csv"))
LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# Redis 快取與 Session 連線
# =========================
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

redis_client = None
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=2)
    redis_client.ping()
    logging.info(f"Redis 快取與 Session 伺服器連線成功：{REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logging.warning(f"Redis 連線失敗，將降級為記憶體 Session 模式：{str(e)}")
    redis_client = None

# 本地記憶體 Fallback Session (當 Redis 無法連線時)
memory_sessions = {}

def get_station_session(station_id: str) -> dict | None:
    if not station_id:
        return None
    session_key = f"station_session:{station_id}"
    if redis_client:
        try:
            data = redis_client.get(session_key)
            if data:
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            logging.warning(f"讀取 Redis 站點 Session 失敗: {e}")
    return memory_sessions.get(station_id)


def set_station_session(station_id: str, session_data: dict, ttl: int = 7200):
    if not station_id:
        return
    session_key = f"station_session:{station_id}"
    if redis_client:
        try:
            redis_client.setex(session_key, ttl, json.dumps(session_data))
            return
        except Exception as e:
            logging.warning(f"寫入 Redis 站點 Session 失敗: {e}")
    memory_sessions[station_id] = session_data


def clear_station_session(station_id: str):
    if not station_id:
        return
    session_key = f"station_session:{station_id}"
    if redis_client:
        try:
            redis_client.delete(session_key)
        except Exception as e:
            logging.warning(f"刪除 Redis 站點 Session 失敗: {e}")
    memory_sessions.pop(station_id, None)


# =========================
# 模型與資源動態載入
# =========================
rf_bundle = None
open_set_predictor = None
admdp_model = None
_model_mtime = None
_openset_mtime = None
_admdp_mtime = None
_asset_lock = Lock()


def load_assets(force=False):
    global rf_bundle, open_set_predictor, admdp_model, _model_mtime, _openset_mtime, _admdp_mtime, MODEL_VERSION

    with _asset_lock:
        if RF_MODEL_PATH.exists():
            mtime = RF_MODEL_PATH.stat().st_mtime
            if force or _model_mtime != mtime:
                rf_bundle = joblib.load(RF_MODEL_PATH)
                metadata = rf_bundle.get("metadata", {})
                MODEL_VERSION = metadata.get("trained_at", MODEL_VERSION)
                _model_mtime = mtime
                logging.info(f"主模型 RF-MCPR 載入成功：{RF_MODEL_PATH}")

        if OPEN_SET_MODEL_PATH.exists():
            os_mtime = OPEN_SET_MODEL_PATH.stat().st_mtime
            if force or _openset_mtime != os_mtime:
                try:
                    open_set_predictor = OpenSetRfMcprPredictor.from_path(OPEN_SET_MODEL_PATH)
                    _openset_mtime = os_mtime
                    logging.info(f"開集門衛模型 Open-Set 載入成功：{OPEN_SET_MODEL_PATH}")
                except Exception as e:
                    logging.warning(f"Open-Set 模型載入失敗: {e}")

        if ADMDP_MODEL_PATH.exists():
            admdp_mtime = ADMDP_MODEL_PATH.stat().st_mtime
            if force or _admdp_mtime != admdp_mtime:
                try:
                    admdp_model = load_admdp_model(ADMDP_MODEL_PATH)
                    _admdp_mtime = admdp_mtime
                    logging.info(f"馬可夫動態決策模型 ADMDP 載入成功：{ADMDP_MODEL_PATH}")
                except Exception as e:
                    logging.warning(f"ADMDP 模型載入失敗: {e}")


try:
    load_assets(force=True)
except Exception as e:
    logging.error(f"模型資源載入失敗: {str(e)}")


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


def parse_repair_suggestion(text):
    if not isinstance(text, str) or text.strip() == "":
        return {"action": None, "part": None, "category": None}

    text = text.strip()
    actions = ["更換", "吹淨", "清潔", "調整", "潤滑", "緊固"]
    for act in actions:
        if text.startswith(act):
            return {
                "action": act,
                "part": text[len(act):].strip(),
                "category": "action"
            }

    system_keywords = ["B機", "系統", "程式", "停止", "偵測", "壓力", "NG"]
    if any(word in text for word in system_keywords):
        return {"action": None, "part": text, "category": "system"}

    return {"action": None, "part": text, "category": "fault"}


def calculate_leak_trend(last_leaks: dict, new_leaks: dict, threshold: float = 0.05) -> str:
    if not last_leaks or not new_leaks:
        return "initial"

    improved_count, same_count, worse_count, valid_count = 0, 0, 0, 0
    for key, new_val in new_leaks.items():
        if key in last_leaks and new_val is not None and last_leaks[key] is not None:
            try:
                delta = float(new_val) - float(last_leaks[key])
                valid_count += 1
                if delta < -abs(threshold):
                    improved_count += 1
                elif delta > abs(threshold):
                    worse_count += 1
                else:
                    same_count += 1
            except (ValueError, TypeError):
                continue

    if valid_count == 0:
        return "unknown"
    if worse_count > improved_count:
        return "worse"
    if improved_count > worse_count:
        return "improved"
    if same_count > 0:
        return "same"
    return "mixed"


# =========================
# 三聯動預測 API (/predict)
# =========================
@app.route("/predict", methods=["POST"])
def predict():
    try:
        load_assets()
        data = request.get_json() or {}
        station_id = str(data.get("station_id", "default_station")).strip()
        ng_items = data.get("ng_items", [])
        leak_values = data.get("leak_values", {})

        # === 0. 產品 PASS (無 NG 項) ➡️ 終止該站點的 ADMDP Session ===
        if not ng_items:
            clear_station_session(station_id)
            resp = {
                "stage": "PASS",
                "suggestions": "產品測試 PASS，站點維修 Session 結案關閉",
                "parts": []
            }
            return jsonify({"success": True, "data": resp})

        # NG 簡碼 → 全名
        translated = []
        for ng in ng_items:
            key = str(ng).lower()
            translated.append(TEST_COLUMNS.get(key, str(ng)))
        resolved_ng_key = ", ".join(sorted(translated))

        # 讀取目前站點 Session
        session = get_station_session(station_id)

        # === 情況 A：站點無 Session ➡️ 【第一次初診】 (Open-Set + RF-MCPR) ===
        if session is None:
            # A1. 開集識別 (Open-Set 門衛)
            open_set_status = "KNOWN"
            if open_set_predictor:
                try:
                    open_report = open_set_predictor.predict(ng_key=resolved_ng_key, top_n=1)
                    if open_report["decision"]["status"] == "unknown":
                        return jsonify({
                            "success": True,
                            "data": {
                                "stage": "OPEN_SET_UNKNOWN",
                                "open_set_status": "UNKNOWN",
                                "warning": "⚠️ 檢測到全新/未知 NG 異常組合，建議由資深工程師特檢判讀",
                                "suggestions": "未知異常組合 (建議人工檢驗)",
                                "parts": []
                            }
                        })
                    open_set_status = open_report["decision"]["status"]
                except Exception as e:
                    logging.warning(f"Open-Set 預測跳過: {e}")

            # A2. RF-MCPR 靜態診斷 (第一次初診只給機率最高的 1 個 Top-1 建議，防止歧義)
            rf_model = rf_bundle["model"]
            ohe = rf_bundle["onehot_encoder"]
            le = rf_bundle["label_encoder"]

            x_sample = ohe.transform(pd.DataFrame({"NG項": [resolved_ng_key]}))
            probs = rf_model.predict_proba(x_sample)[0]

            top1_idx = probs.argmax()
            top1_suggestion = normalize_repair_suggestion(le.classes_[top1_idx])
            top1_prob = float(probs[top1_idx])

            parsed = parse_repair_suggestion(top1_suggestion)
            parts = [parsed["part"]] if parsed["part"] else []

            # 建立站點 Session (記錄最高機率的 Top-1 建議為 prev_action)
            new_session = {
                "station_id": station_id,
                "attempt_count": 1,
                "initial_ng_key": resolved_ng_key,
                "prev_action": top1_suggestion,
                "last_leak_values": leak_values,
                "created_at": datetime.now().isoformat()
            }
            set_station_session(station_id, new_session)

            response_data = {
                "stage": "STAGE_1_RF_MCPR",
                "open_set_status": open_set_status,
                "suggestions": f"{top1_suggestion} ({top1_prob:.2f})",
                "top1_suggestion": top1_suggestion,
                "probability": top1_prob,
                "parts": parts,
                "station_session": {"station_id": station_id, "attempt_count": 1}
            }
            return jsonify({"success": True, "data": response_data})

        # === 情況 B：站點已有 Session ➡️ 【第二次+ 複診修訂】 (ADMDP 馬可夫鏈) ===
        attempt_count = session.get("attempt_count", 1) + 1
        prev_action = session.get("prev_action", "")
        last_leaks = session.get("last_leak_values", {})

        # 1. 計算前後洩漏量趨勢 (trend)
        trend = calculate_leak_trend(last_leaks, leak_values)

        # 2. 組合 ADMDP 狀態 Key
        admdp_state = f"ng={resolved_ng_key} | trend={trend} | prev={prev_action}"

        admdp_rec = None
        if admdp_model:
            try:
                admdp_rec = recommend_from_state(admdp_state, model=admdp_model, top_n=1)
            except Exception as e:
                logging.warning(f"ADMDP 推論警告: {e}")

        final_suggestion = None
        source_stage = "STAGE_2_ADMDP"
        reason_msg = f"站點第 {attempt_count} 次複診：前次「{prev_action}」後洩漏量趨勢為 {trend}，ADMDP 馬可夫鏈動態推薦新建議"

        if admdp_rec and admdp_rec.get("best_action"):
            final_suggestion = admdp_rec["best_action"]
        else:
            # ADMDP State Miss ➡️ 降級退路：取 RF-MCPR 並強迫過濾掉上一次失敗動作 (prev_action)
            rf_model = rf_bundle["model"]
            ohe = rf_bundle["onehot_encoder"]
            le = rf_bundle["label_encoder"]
            x_sample = ohe.transform(pd.DataFrame({"NG項": [resolved_ng_key]}))
            probs = rf_model.predict_proba(x_sample)[0]

            ranked_indices = probs.argsort()[::-1]
            for idx in ranked_indices:
                sug = normalize_repair_suggestion(le.classes_[idx])
                if sug != prev_action:
                    final_suggestion = sug
                    break
            if not final_suggestion:
                final_suggestion = prev_action
            source_stage = "STAGE_2_ADMDP_FALLBACK"
            reason_msg = f"ADMDP 狀態未命中，自動啟動退路機制：過濾掉前次「{prev_action}」，推薦次佳處置建議"

        parsed = parse_repair_suggestion(final_suggestion)
        parts = [parsed["part"]] if parsed["part"] else []

        # 3. 更新 Redis 站點 Session
        session["attempt_count"] = attempt_count
        session["prev_action"] = final_suggestion
        session["last_leak_values"] = leak_values
        set_station_session(station_id, session)

        response_data = {
            "stage": source_stage,
            "suggestions": final_suggestion,
            "reason": reason_msg,
            "parts": parts,
            "station_session": {"station_id": station_id, "attempt_count": attempt_count}
        }
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
