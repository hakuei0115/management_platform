from __future__ import annotations

from datetime import datetime
from io import BytesIO
import os
from pathlib import Path

from flask import Flask, render_template_string, request, send_from_directory, url_for
import pandas as pd

from excel_merge_pipeline import dataframe_to_excel_bytes, merge_excel_sources
from generate_ng_rules import generate_ng_rules
from rf_mcpr_training import train_rf_mcpr
from open_set_rf_training import train_open_set_rf_mcpr
from admdp_training import train_admdp_from_excel, train_admdp_policy
from admdp_dataset import build_admdp_transitions


app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.environ.get("TRAIN_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PREDICT_DATA_DIR = Path(
    os.environ.get("MODEL_PREDICT_DATA_DIR", PROJECT_ROOT.parent / "model_predict" / "data")
)
MODEL_PREDICT_MODEL_DIR = Path(
    os.environ.get("MODEL_PREDICT_MODEL_DIR", PROJECT_ROOT.parent / "model_predict" / "model")
)
RULES_FILENAME = os.environ.get("MODEL_RULES_FILENAME", "NG項_最終維修建議對照.csv")
MODEL_FILENAME = os.environ.get("MODEL_FILENAME", "rf_mcpr.pkl")
OPEN_SET_MODEL_FILENAME = "open_set_rf_mcpr.pkl"
ADMDP_MODEL_FILENAME = "admdp_policy.pkl"

MODEL_PREDICT_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PREDICT_MODEL_DIR.mkdir(parents=True, exist_ok=True)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI 多模型一體化訓練工具</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d9e2ec;
      --accent: #1769aa;
      --accent-strong: #0f4c81;
      --ok: #146c43;
      --warn: #9a5b00;
      --error: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 18px 28px;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }
    main {
      width: min(1120px, calc(100vw - 32px));
      margin: 24px auto 40px;
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 20px;
      align-items: start;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0;
    }
    label {
      display: block;
      font-size: 14px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    input[type="file"] {
      width: 100%;
      border: 1px dashed #9fb3c8;
      border-radius: 8px;
      background: #fbfdff;
      padding: 18px;
      font-size: 15px;
    }
    .options {
      display: grid;
      gap: 10px;
      margin: 18px 0;
    }
    .check {
      display: flex;
      gap: 10px;
      align-items: center;
      color: var(--text);
      font-size: 14px;
      margin: 0;
    }
    .check input {
      width: 18px;
      height: 18px;
      accent-color: var(--accent);
    }
    button, .download-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      font-size: 14px;
      padding: 0 16px;
      text-decoration: none;
      cursor: pointer;
    }
    button.btn-sec {
      background: #4b5563;
    }
    button.btn-sec:hover {
      background: #374151;
    }
    button.btn-success {
      background: #059669;
    }
    button.btn-success:hover {
      background: #047857;
    }
    button:hover, .download-link:hover {
      background: var(--accent-strong);
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      min-height: 74px;
      background: #fbfcfe;
    }
    .metric strong {
      display: block;
      font-size: 24px;
      line-height: 1.15;
      letter-spacing: 0;
    }
    .metric span {
      color: var(--muted);
      font-size: 13px;
    }
    .message {
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 16px;
      border: 1px solid var(--line);
      background: #fbfcfe;
      color: var(--muted);
      font-size: 14px;
    }
    .message.error {
      border-color: #f3b2aa;
      background: #fff5f5;
      color: var(--error);
    }
    .message.ok {
      border-color: #9cd6b6;
      background: #f0fff7;
      color: var(--ok);
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .chart {
      margin-top: 14px;
      display: grid;
      gap: 9px;
    }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(120px, 220px) 1fr 56px;
      gap: 10px;
      align-items: center;
      font-size: 13px;
    }
    .bar-label { overflow-wrap: anywhere; }
    .bar-track {
      height: 12px;
      border-radius: 999px;
      background: #e8eef5;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      border-radius: 999px;
      background: var(--accent);
    }
    .subtle {
      color: var(--muted);
      font-size: 13px;
      margin: 10px 0 0;
    }
    .stack {
      display: grid;
      gap: 20px;
      align-items: start;
    }
    .divider {
      height: 1px;
      background: var(--line);
      margin: 18px 0;
    }
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
    }
    .loading-overlay.active {
      opacity: 1;
      pointer-events: auto;
    }
    .spinner-card {
      background: #ffffff;
      border-radius: 12px;
      padding: 36px 44px;
      text-align: center;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      max-width: 380px;
    }
    .spinner {
      width: 52px;
      height: 52px;
      margin: 0 auto 20px;
      border: 5px solid #e2e8f0;
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .loading-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
    }
    .loading-subtext {
      font-size: 13px;
      color: var(--muted);
      line-height: 1.5;
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
      .bar-row { grid-template-columns: 1fr; gap: 5px; }
    }
  </style>
  </head>
  <body>
    <!-- 全螢幕 Loading 載入等待遮罩 -->
    <div id="loadingOverlay" class="loading-overlay">
      <div class="spinner-card">
        <div class="spinner"></div>
        <div id="loadingTitle" class="loading-title">AI 計算中，請稍候...</div>
        <div class="loading-subtext">正在進行模型計算與權重寫入，請勿關閉或刷新網頁</div>
      </div>
    </div>

    <header>
      <h1>AI 多模型一體化訓練工具 (RF-MCPR + Open-Set + ADMDP)</h1>
    </header>
    <main>
      <div class="stack">
        <!-- 步驟 1：資料集處理區塊 -->
        <section>
          <h2>步驟 1：資料集處理 (Excel 合併與資料集生成)</h2>
          {% if mode == "dataset" and error %}
            <div class="message error">{{ error }}</div>
          {% elif mode == "dataset" and (output_file or stats_file) %}
            <div class="message ok">
              {% if output_file %}✅ 已成功產生合併 Excel: {{ output_file }}<br>{% endif %}
              {% if stats_file %}✅ 已成功產生全套訓練資料集 (NG對照表 + ADMDP轉移鏈集)，並同步更新至 model_predict/data/{% endif %}
            </div>
          {% else %}
            <div class="message">上傳產線原始 Excel 檔案，可選擇僅合併 Excel 或生成全套訓練資料集。</div>
          {% endif %}
          <form method="post" action="{{ url_for('merge') }}" enctype="multipart/form-data">
            <label for="files">Excel 檔案 (.xlsx)</label>
            <input id="files" name="files" type="file" accept=".xlsx" multiple required>
            <div class="options">
              <label class="check">
                <input type="checkbox" name="include_source_columns">
                <span>輸出來源檔案、工作表、原始異常編號</span>
              </label>
              <label class="check">
                <input type="checkbox" name="keep_extra_columns">
                <span>保留非 train_data 樣板欄位</span>
              </label>
            </div>
            <div class="button-row">
              <button type="submit" name="action" value="merge" class="btn-sec">產生合併 Excel</button>
              <button type="submit" name="action" value="dataset">產生訓練集 (NG對照, ADMDP轉移鏈, 開集識別)</button>
              {% if output_file %}
                <a class="download-link" href="{{ url_for('download_file', filename=output_file) }}">下載 Excel</a>
              {% endif %}
              {% if stats_file %}
                <a class="download-link" href="{{ url_for('download_file', filename=stats_file) }}">下載 NG對照 CSV</a>
              {% endif %}
              {% if admdp_ds_file %}
                <a class="download-link" href="{{ url_for('download_file', filename=admdp_ds_file) }}">下載 ADMDP轉移鏈 CSV</a>
              {% endif %}
            </div>
          </form>
        </section>

        <!-- 步驟 2：AI 模型訓練區塊 -->
        <section>
          <h2>步驟 2：AI 模型訓練專區</h2>
          {% if mode == "csv_train" and error %}
            <div class="message error">{{ error }}</div>
          {% elif mode == "csv_train" and trained_msg %}
            <div class="message ok">
              {{ trained_msg|safe }}
            </div>
          {% else %}
            <div class="message">上傳對應訓練資料集進行訓練。<strong>一鍵全套訓練</strong> 需同時具備 <code>NG對照表</code> 與 <code>ADMDP 轉移鏈 CSV</code>。</div>
          {% endif %}
          <form method="post" action="{{ url_for('train_from_csv') }}" enctype="multipart/form-data">
            <label for="rules_file">1. NG項_最終維修建議對照.csv (用於 RF-MCPR 與 Open-Set)</label>
            <input id="rules_file" name="rules_file" type="file" accept=".csv">
            
            <label for="admdp_file" style="margin-top: 14px;">2. admdp_transitions.csv 轉移鏈檔 (用於 ADMDP，可選擇上傳或使用步驟 1 產生檔)</label>
            <input id="admdp_file" name="admdp_file" type="file" accept=".csv">
            
            <div style="margin-top: 18px;">
              <button type="submit" name="train_target" value="all" class="btn-success" style="width: 100%; font-size: 15px;">
                一鍵訓練全套 AI 模型 (RF-MCPR + Open-Set + ADMDP)
              </button>
            </div>

            <div class="divider"></div>
            
            <label>獨立單獨訓練專區：</label>
            <div class="button-row">
              <button type="submit" name="train_target" value="rf" class="btn-sec">單獨訓練 RF-MCPR</button>
              <button type="submit" name="train_target" value="openset" class="btn-sec">單獨訓練 Open-Set 開集識別</button>
              <button type="submit" name="train_target" value="admdp" class="btn-sec">單獨訓練 ADMDP 馬可夫決策</button>
            </div>
          </form>
        </section>
      </div>

      <!-- 統計資料與模型評估看板 -->
      <section>
        <h2>模型評估與統計數據看板</h2>
        {% if error and mode not in ["dataset", "csv_train"] %}
          <div class="message error">{{ error }}</div>
        {% endif %}

        {% if rule_stats %}
          <h2 style="margin-top: 10px;">資料集規模統計</h2>
          <div class="metrics">
            <div class="metric"><strong>{{ rule_stats.output_rows }}</strong><span>NG 對照總筆數</span></div>
            <div class="metric"><strong>{{ rule_stats.unique_ng_items }}</strong><span>獨立 NG 組合數</span></div>
            <div class="metric"><strong>{{ rule_stats.unique_repairs }}</strong><span>維修建議類別數</span></div>
            <div class="metric"><strong>{{ rule_stats.groups_with_pass }}</strong><span>有 PASS 紀錄案例</span></div>
          </div>
        {% endif %}

        {% if training %}
          <h2 style="margin-top: 20px;">RF-MCPR 主模型評估 (靜態診斷)</h2>
          <div class="metrics">
            <div class="metric"><strong>{{ percent(training.metrics.accuracy) }}</strong><span>Accuracy</span></div>
            <div class="metric"><strong>{{ percent(training.metrics.precision_weighted) }}</strong><span>Weighted Precision</span></div>
            <div class="metric"><strong>{{ percent(training.metrics.recall_weighted) }}</strong><span>Weighted Recall</span></div>
            <div class="metric"><strong>{{ percent(training.metrics.f1_weighted) }}</strong><span>Weighted F1</span></div>
          </div>
          <p class="subtle">
            切分策略：{{ training.metrics.split_strategy }} | 訓練集: {{ training.metrics.train_rows }} 筆 | 測試集: {{ training.metrics.test_rows }} 筆
          </p>
        {% endif %}

        {% if open_set_training %}
          <h2 style="margin-top: 20px;">Open-Set 開集識別評估 (防衛門衛)</h2>
          <div class="metrics">
            <div class="metric"><strong>{{ percent(open_set_training.non_unknown_coverage) }}</strong><span>高信心覆蓋率</span></div>
            <div class="metric"><strong>{{ percent(open_set_training.confident_accuracy) if open_set_training.confident_accuracy else 'N/A' }}</strong><span>高信心準確率</span></div>
            <div class="metric"><strong>{{ open_set_training.unknown_count }} 筆</strong><span>開集未知阻斷數</span></div>
            <div class="metric"><strong>{{ open_set_training.total_rows }} 筆</strong><span>驗證總筆數</span></div>
          </div>
        {% endif %}

        {% if admdp_trained %}
          <h2 style="margin-top: 20px;">ADMDP 馬可夫動態決策模型 (動態追蹤)</h2>
          <div class="message ok">
            ✅ 吸收馬可夫動態決策鏈 Policy 已成功訓練並儲存至 <code>model_predict/model/admdp_policy.pkl</code>！
          </div>
        {% endif %}

        {% if training and training.class_metrics %}
          <h2 style="margin-top: 20px;">類別召回率 Top-10</h2>
          <div class="chart">
            {% for item in training.class_metrics[:10] %}
              <div class="bar-row">
                <div class="bar-label">{{ item.label }} / {{ item.support }} 筆</div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: {{ width_pct(item.recall) }}%;"></div>
                </div>
                <div>{{ percent(item.recall) }}</div>
              </div>
            {% endfor %}
          </div>
        {% endif %}
      </section>
    </main>

    <script>
      document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
          const submitter = e.submitter;
          let title = '資料處理中，請稍候...';
          if (submitter) {
            const val = submitter.value;
            if (val === 'all') {
              title = '全套 AI 模型一體化訓練中...';
            } else if (val === 'rf') {
              title = '主模型 RF-MCPR 訓練中...';
            } else if (val === 'openset') {
              title = '開集識別 Open-Set 訓練中...';
            } else if (val === 'admdp') {
              title = 'ADMDP 馬可夫決策鏈訓練中...';
            } else if (val === 'dataset') {
              title = '解析產線紀錄 & 建立全套訓練集...';
            } else if (val === 'merge') {
              title = '產線原始 Excel 合併中...';
            }
          }
          document.getElementById('loadingTitle').innerText = title;
          document.getElementById('loadingOverlay').classList.add('active');
        });
      });
    </script>
  </body>
</html>
"""


@app.get("/")
def index():
    return render_page()


@app.post("/merge")
def merge():
    uploads = [file for file in request.files.getlist("files") if file and file.filename]
    if not uploads:
        return render_page(error="請選擇至少一個 .xlsx 檔案")

    sources = [(upload.filename, upload.read()) for upload in uploads]
    result = merge_excel_sources(
        sources,
        include_source_columns="include_source_columns" in request.form,
        keep_extra_columns="keep_extra_columns" in request.form,
    )

    if result.dataframe.empty:
        return render_page(error="沒有可合併的有效資料工作表", result=result)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    action = request.form.get("action", "merge")

    if action == "dataset":
        try:
            rules, rule_stats = generate_ng_rules(result.dataframe)
        except Exception as exc:
            return render_page(error=f"建立統計資料失敗：{exc}", result=result)

        # 1. 產生 NG對照表 CSV
        stats_name = f"NG項_最終維修建議對照_{timestamp}.csv"
        stats_path = output_path_for(stats_name)
        rules.to_csv(stats_path, index=False, encoding="utf-8-sig")
        write_shared_rules_csv(rules)

        # 2. 產生 合併 Excel
        output_name = f"merged_train_data_{timestamp}.xlsx"
        output_path = output_path_for(output_name)
        output_path.write_bytes(dataframe_to_excel_bytes(result.dataframe))

        # 3. 產生 ADMDP 狀態轉移鏈 CSV
        admdp_ds_name = f"admdp_transitions_{timestamp}.csv"
        admdp_ds_path = output_path_for(admdp_ds_name)
        try:
            admdp_res = build_admdp_transitions(result.dataframe)
            admdp_res.transitions.to_csv(admdp_ds_path, index=False, encoding="utf-8-sig")
            admdp_res.transitions.to_csv(MODEL_PREDICT_DATA_DIR / "admdp_transitions.csv", index=False, encoding="utf-8-sig")
        except Exception as admdp_ds_err:
            print("⚠️ ADMDP 轉移鏈資料集生成提醒:", admdp_ds_err)
            admdp_ds_name = ""

        return render_page(
            result=result,
            output_file=output_name,
            stats_file=stats_name,
            admdp_ds_file=admdp_ds_name,
            rule_stats=rule_stats.as_dict(),
            mode="dataset",
        )

    output_name = f"merged_train_data_{timestamp}.xlsx"
    output_path = output_path_for(output_name)
    output_path.write_bytes(dataframe_to_excel_bytes(result.dataframe))

    return render_page(result=result, output_file=output_name, mode="dataset")


@app.get("/download/<path:filename>")
def download_file(filename: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.post("/train-from-csv")
def train_from_csv():
    train_target = request.form.get("train_target", "all")
    rules_upload = request.files.get("rules_file")
    admdp_upload = request.files.get("admdp_file")

    training = None
    open_set_training = None
    admdp_trained = False
    trained_messages = []

    # 1. 讀取或保存上傳的 rules CSV (NG對照表)
    rules = None
    if rules_upload and rules_upload.filename:
        try:
            content = rules_upload.read()
            rules = read_rules_csv(content)
            write_shared_rules_csv(rules)
        except Exception as exc:
            return render_page(error=f"讀取 NG對照表 CSV 失敗：{exc}", mode="csv_train")
    elif shared_rules_path().exists():
        try:
            rules = pd.read_csv(shared_rules_path(), encoding="utf-8-sig")
        except Exception:
            pass

    # 2. 讀取或保存上傳的 admdp CSV (轉移鏈檔)
    admdp_trans_df = None
    if admdp_upload and admdp_upload.filename:
        try:
            admdp_content = admdp_upload.read()
            admdp_trans_df = pd.read_csv(BytesIO(admdp_content), encoding="utf-8-sig")
            admdp_trans_df.to_csv(MODEL_PREDICT_DATA_DIR / "admdp_transitions.csv", index=False, encoding="utf-8-sig")
        except Exception as exc:
            return render_page(error=f"讀取 ADMDP 轉移鏈 CSV 失敗：{exc}", mode="csv_train")
    elif (MODEL_PREDICT_DATA_DIR / "admdp_transitions.csv").exists():
        try:
            admdp_trans_df = pd.read_csv(MODEL_PREDICT_DATA_DIR / "admdp_transitions.csv", encoding="utf-8-sig")
        except Exception:
            pass

    # === 一鍵訓練全套 AI 模型 (Mandatory Requirement) ===
    if train_target == "all":
        if rules is None:
            return render_page(error="⚠️ 一鍵訓練全套 AI 需提供【1. NG項_最終維修建議對照.csv】，請選擇上傳或先於步驟 1 產生訓練集！", mode="csv_train")
        if admdp_trans_df is None:
            return render_page(error="⚠️ 一鍵訓練全套 AI 需同時提供【2. admdp_transitions.csv 轉移鏈檔】，請選擇上傳或先於步驟 1 產生訓練集！", mode="csv_train")

        try:
            # 🟢 1. 訓練 RF-MCPR 主模型
            training = train_rf_mcpr(rules, model_path=shared_model_path())
            trained_messages.append("1. 主模型 <code>rf_mcpr.pkl</code> 訓練完成")

            # 🛡️ 2. 訓練 Open-Set 開集識別
            open_set_res = train_open_set_rf_mcpr(rules, model_path=MODEL_PREDICT_MODEL_DIR / OPEN_SET_MODEL_FILENAME)
            open_set_training = open_set_res.validation
            trained_messages.append("2. 開集識別模型 <code>open_set_rf_mcpr.pkl</code> 訓練完成")

            # 🔄 3. 訓練 ADMDP 馬可夫動態決策
            train_admdp_policy(admdp_trans_df, model_path=MODEL_PREDICT_MODEL_DIR / ADMDP_MODEL_FILENAME)
            admdp_trained = True
            trained_messages.append("3. 馬可夫動態決策 <code>admdp_policy.pkl</code> 訓練完成")

        except Exception as exc:
            return render_page(error=f"全套模型訓練失敗：{exc}", mode="csv_train")

    elif train_target == "rf":
        if rules is None:
            return render_page(error="請上傳【1. NG項_最終維修建議對照.csv】以進行 RF-MCPR 訓練", mode="csv_train")
        training = train_rf_mcpr(rules, model_path=shared_model_path())
        trained_messages.append("1. 主模型 <code>rf_mcpr.pkl</code> 訓練完成")

    elif train_target == "openset":
        if rules is None:
            return render_page(error="請上傳【1. NG項_最終維修建議對照.csv】以進行 Open-Set 訓練", mode="csv_train")
        open_set_res = train_open_set_rf_mcpr(rules, model_path=MODEL_PREDICT_MODEL_DIR / OPEN_SET_MODEL_FILENAME)
        open_set_training = open_set_res.validation
        trained_messages.append("2. 開集識別模型 <code>open_set_rf_mcpr.pkl</code> 訓練完成")

    elif train_target == "admdp":
        if admdp_trans_df is None:
            return render_page(error="請上傳【2. admdp_transitions.csv 轉移鏈檔】以進行 ADMDP 訓練", mode="csv_train")
        train_admdp_policy(admdp_trans_df, model_path=MODEL_PREDICT_MODEL_DIR / ADMDP_MODEL_FILENAME)
        admdp_trained = True
        trained_messages.append("3. 馬可夫動態決策 <code>admdp_policy.pkl</code> 訓練完成")

    rule_stats = None
    if rules is not None:
        rule_stats = {
            "output_rows": int(len(rules)),
            "unique_ng_items": int(rules["NG項"].nunique()) if "NG項" in rules else 0,
            "unique_repairs": int(rules["維修建議"].nunique()) if "維修建議" in rules else 0,
            "groups_with_pass": int(rules["異常編號"].nunique()) if "異常編號" in rules else 0,
        }

    trained_msg = "✅ 訓練結果：<br>" + "<br>".join(trained_messages) if trained_messages else "已完成訓練"

    return render_page(
        rule_stats=rule_stats,
        training=training,
        open_set_training=open_set_training,
        admdp_trained=admdp_trained,
        trained_msg=trained_msg,
        mode="csv_train",
    )


def render_page(
    error: str = "",
    result=None,
    output_file: str = "",
    stats_file: str = "",
    admdp_ds_file: str = "",
    rule_stats: dict[str, int] | None = None,
    training=None,
    open_set_training=None,
    admdp_trained: bool = False,
    trained_msg: str = "",
    mode: str = "",
):
    summary = {
        "loaded_sheets": 0,
        "skipped_sheets": 0,
        "output_rows": 0,
        "output_columns": 0,
        "unique_cases": 0,
        "duplicate_case_rows": 0,
    }
    reports = []
    warnings = []
    if result is not None:
        summary.update(result.summary())
        reports = result.sheet_reports
        warnings = result.warnings

    return render_template_string(
        PAGE_TEMPLATE,
        error=error,
        summary=summary,
        reports=reports,
        warnings=warnings,
        output_file=output_file,
        stats_file=stats_file,
        admdp_ds_file=admdp_ds_file,
        rule_stats=rule_stats,
        training=training,
        open_set_training=open_set_training,
        admdp_trained=admdp_trained,
        trained_msg=trained_msg,
        mode=mode,
        percent=percent,
        width_pct=width_pct,
        count_width=count_width,
        shared_rules_path=shared_rules_path(),
        shared_model_path=shared_model_path(),
    )


def percent(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def width_pct(value) -> float:
    if value is None:
        return 0
    return max(0, min(100, float(value) * 100))


def count_width(count: int, records: list[dict]) -> float:
    max_count = max((int(item["count"]) for item in records), default=1)
    if max_count <= 0:
        return 0
    return max(4, min(100, int(count) / max_count * 100))


def output_path_for(filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / filename


def shared_rules_path() -> Path:
    return MODEL_PREDICT_DATA_DIR / RULES_FILENAME


def shared_model_path() -> Path:
    return MODEL_PREDICT_MODEL_DIR / MODEL_FILENAME


def write_shared_rules_csv(rules: pd.DataFrame) -> Path:
    path = shared_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    rules.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def read_rules_csv(content: bytes) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            return pd.read_csv(BytesIO(content), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise ValueError(f"CSV 編碼無法辨識：{last_error}")


if __name__ == "__main__":
    port = int(os.environ.get("MERGE_GUI_PORT", "8501"))
    app.run(host="0.0.0.0", port=port, debug=False)
