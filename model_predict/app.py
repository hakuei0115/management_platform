import joblib
import pandas as pd
import logging
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MODEL_VERSION = "v1.0.0"

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# 模型載入
# =========================
try:
    bundle = joblib.load("model/rf_mcpr.pkl")
    rf = bundle["model"]
    ohe = bundle["onehot_encoder"]
    le = bundle["label_encoder"]
    df_train = pd.read_csv("NG項_最終維修建議對照.csv")
    logging.info("模型載入成功")
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
# 維修建議解析器（強化版）
# =========================
def parse_repair_suggestion(text):
    """
    將維修建議拆解成 action / part / category
    支援三種型態：
    (A) 更換帽型蓋 → action + part
    (B) D3環脫落 → 故障部位
    (C) B機檢測NG → 系統異常
    """
    if not isinstance(text, str) or text.strip() == "":
        return {"action": None, "part": None, "category": None}

    text = text.strip()

    # (A) 動詞 + 名詞形式
    actions = ["更換", "吹淨", "清潔", "調整", "潤滑", "緊固"]
    for act in actions:
        if text.startswith(act):
            part = text[len(act):].strip()
            return {"action": act, "part": part, "category": "action"}

    # (C) 系統型異常
    system_keywords = ["B機", "系統", "程式", "停止", "偵測", "壓力", "NG"]
    if any(word in text for word in system_keywords):
        return {"action": None, "part": text, "category": "system"}

    # (B) 其他 → 故障部位
    return {"action": None, "part": text, "category": "fault"}


def predict_topn(ng_key, n=5):
    try:
        X_sample = ohe.transform(pd.DataFrame({"NG項": [ng_key]}))
        probs = rf.predict_proba(X_sample)[0]

        df_prob = pd.DataFrame({
            "維修建議": le.classes_,
            "機率": probs
        })

        # 只挑訓練資料中出現過的維修建議（避免 0% 垃圾類別）
        valid = df_train[df_train["NG項"] == ng_key]["維修建議"].unique()
        df_filtered = (
            df_prob[df_prob["維修建議"].isin(valid)]
            .sort_values("機率", ascending=False)
            .reset_index(drop=True)
        )

        # 套入你的解析器
        results = []
        for _, row in df_filtered.head(n).iterrows():
            parsed = parse_repair_suggestion(row["維修建議"])
            results.append({
                "suggestion": row["維修建議"],
                "probability": float(row["機率"]),
                "action": parsed["action"],
                "part": parsed["part"],
                "category": parsed["category"]
            })

        return results

    except Exception as e:
        logging.error(f"predict_topn 錯誤: {str(e)}")
        return []


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        ng_items = data.get("ng_items", [])
        top_n = data.get("top_n", 5)

        # ==============================
        # ★ Step1: 先把代碼轉成完整測試名稱
        # ==============================
        translated_list = []
        for ng in ng_items:
            if ng not in TEST_COLUMNS:
                return jsonify({
                    "success": False,
                    "error": f"未知的 NG 項目：{ng}"
                }), 400

            translated_list.append(TEST_COLUMNS[ng])

        # ==============================
        # ★ Step2: Sort（避免 M08+M11 與 M11+M08 被當不同）
        # ==============================
        translated_list_sorted = sorted(translated_list)

        # ==============================
        # ★ Step3: 合併成 ng_key（模型吃這個）
        # ==============================
        ng_key = ", ".join(translated_list_sorted)

        # ==============================
        # ★ Step4: 丟入模型做預測
        # ==============================
        predictions = predict_topn(ng_key, top_n)

        # ==============================
        # Log
        # ==============================
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "model_version": MODEL_VERSION,
            "input_ng_items": ng_items,
            "translated_items": translated_list_sorted,
            "ng_key": ng_key,
            "top_n": top_n,
            "outputs": predictions
        }

        pd.DataFrame([log_record]).to_csv(
            "logs/prediction_history.csv",
            mode="a",
            index=False,
            header=False
        )

        logging.info(f"預測成功: {log_record}")

        # === 5️⃣ 可能維修部位列表 ===
        likely_parts = []
        for item in predictions:
            part = item["part"]
            if part and part not in likely_parts:
                likely_parts.append(part)

        # === 6️⃣ suggestions 字串版 ===
        suggestions_str_list = []
        for item in predictions:
            prob = f"{item['probability']:.2f}"
            suggestions_str_list.append(f"{item['suggestion']}({prob})")

        suggestions_str = ", ".join(suggestions_str_list)

        # === 7️⃣ 回傳資料 ===
        response_data = {
            "suggestions": suggestions_str,     # ← 你要的字串
            "parts": likely_parts
        }

        return jsonify({
            "success": True,
            "data": response_data,
            "message": "prediction successful"
        })

    except Exception as e:
        error_msg = traceback.format_exc()
        logging.error(error_msg)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_msg
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
