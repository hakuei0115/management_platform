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

MODEL_PREDICT_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PREDICT_MODEL_DIR.mkdir(parents=True, exist_ok=True)


PAGE_TEMPLATE = """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RF-MCPR 訓練工具</title>
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
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 700;
      background: #fbfcfe;
    }
    .warnings {
      margin: 14px 0 0;
      padding-left: 18px;
      color: var(--warn);
      font-size: 13px;
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
    .bar-label {
      overflow-wrap: anywhere;
    }
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
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
      .bar-row { grid-template-columns: 1fr; gap: 5px; }
    }
  </style>
  </head>
  <body>
    <header>
    <h1>RF-MCPR 訓練工具</h1>
  </header>
  <main>
    <div class="stack">
    <section>
      <h2>建立訓練資料集</h2>
      {% if mode == "dataset" and error %}
        <div class="message error">{{ error }}</div>
      {% elif mode == "dataset" and (output_file or stats_file) %}
        <div class="message ok">
          {% if output_file %}已建立 {{ output_file }}{% endif %}
          {% if stats_file %}已建立 {{ stats_file }}，並更新 {{ shared_rules_path }}{% endif %}
        </div>
      {% else %}
        <div class="message">異常編號會自動轉換格式。</div>
      {% endif %}
      <form method="post" action="{{ url_for('merge') }}" enctype="multipart/form-data">
        <label for="files">Excel 檔案</label>
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
          <button type="submit" name="action" value="merge">產生合併 Excel</button>
          <button type="submit" name="action" value="stats">產生 NG 對照 CSV</button>
          {% if output_file %}
            <a class="download-link" href="{{ url_for('download_file', filename=output_file) }}">下載結果</a>
          {% endif %}
          {% if mode == "dataset" and stats_file %}
            <a class="download-link" href="{{ url_for('download_file', filename=stats_file) }}">下載 CSV</a>
          {% endif %}
        </div>
      </form>
    </section>

    <section>
      <h2>訓練 RF-MCPR</h2>
      {% if mode == "csv_train" and error %}
        <div class="message error">{{ error }}</div>
      {% elif mode == "csv_train" and training %}
        <div class="message ok">模型已儲存到 {{ shared_model_path }}，並更新 {{ shared_rules_path }}</div>
      {% else %}
        <div class="message">上傳已建立好的 NG項_最終維修建議對照.csv 來訓練模型。</div>
      {% endif %}
      <form method="post" action="{{ url_for('train_from_csv') }}" enctype="multipart/form-data">
        <label for="rules_file">NG項_最終維修建議對照.csv</label>
        <input id="rules_file" name="rules_file" type="file" accept=".csv" required>
        <div class="button-row" style="margin-top: 16px;">
          <button type="submit">用 CSV 訓練 RF-MCPR</button>
        </div>
      </form>
    </section>
    </div>

    <section>
      <h2>統計資料</h2>
      {% if error and mode not in ["dataset", "csv_train"] %}
        <div class="message error">{{ error }}</div>
      {% endif %}
      <div class="metrics">
        <div class="metric"><strong>{{ summary.loaded_sheets }}</strong><span>已讀工作表</span></div>
        <div class="metric"><strong>{{ summary.skipped_sheets }}</strong><span>略過工作表</span></div>
        <div class="metric"><strong>{{ summary.output_rows }}</strong><span>輸出列數</span></div>
        <div class="metric"><strong>{{ summary.unique_cases }}</strong><span>異常案例數</span></div>
      </div>
      {% if rule_stats %}
        <h2 style="margin-top: 20px;">統計資料</h2>
        <div class="metrics">
          <div class="metric"><strong>{{ rule_stats.output_rows }}</strong><span>NG 對照列數</span></div>
          <div class="metric"><strong>{{ rule_stats.unique_ng_items }}</strong><span>NG 組合數</span></div>
          <div class="metric"><strong>{{ rule_stats.unique_repairs }}</strong><span>維修建議數</span></div>
          <div class="metric"><strong>{{ rule_stats.groups_with_pass }}</strong><span>有 PASS 案例</span></div>
        </div>
      {% endif %}
      {% if training %}
        <h2 style="margin-top: 20px;">RF-MCPR 評估</h2>
        <div class="metrics">
          <div class="metric"><strong>{{ percent(training.metrics.accuracy) }}</strong><span>Accuracy</span></div>
          <div class="metric"><strong>{{ percent(training.metrics.precision_weighted) }}</strong><span>Weighted Precision</span></div>
          <div class="metric"><strong>{{ percent(training.metrics.recall_weighted) }}</strong><span>Weighted Recall</span></div>
          <div class="metric"><strong>{{ percent(training.metrics.f1_weighted) }}</strong><span>Weighted F1</span></div>
        </div>
        <p class="subtle">
          評估切分：{{ training.metrics.split_strategy }}，
          訓練 {{ training.metrics.train_rows }} 筆，測試 {{ training.metrics.test_rows }} 筆。
          模型已儲存：{{ training.model_path }}
        </p>
        {% if training.class_metrics %}
          <h2 style="margin-top: 20px;">類別召回率</h2>
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
        {% if training.top_repair_counts %}
          <h2 style="margin-top: 20px;">維修建議分布</h2>
          <div class="chart">
            {% for item in training.top_repair_counts %}
              <div class="bar-row">
                <div class="bar-label">{{ item.label }}</div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: {{ count_width(item.count, training.top_repair_counts) }}%;"></div>
                </div>
                <div>{{ item.count }}</div>
              </div>
            {% endfor %}
          </div>
        {% endif %}
        {% if training.top_ng_counts %}
          <h2 style="margin-top: 20px;">NG 組合分布</h2>
          <div class="chart">
            {% for item in training.top_ng_counts %}
              <div class="bar-row">
                <div class="bar-label">{{ item.label }}</div>
                <div class="bar-track">
                  <div class="bar-fill" style="width: {{ count_width(item.count, training.top_ng_counts) }}%;"></div>
                </div>
                <div>{{ item.count }}</div>
              </div>
            {% endfor %}
          </div>
        {% endif %}
      {% endif %}
      {% if warnings %}
        <ul class="warnings">
          {% for warning in warnings[:6] %}
            <li>{{ warning }}</li>
          {% endfor %}
          {% if warnings|length > 6 %}
            <li>另有 {{ warnings|length - 6 }} 筆提醒</li>
          {% endif %}
        </ul>
      {% endif %}
      {% if reports %}
        <table>
          <thead>
            <tr>
              <th>檔案</th>
              <th>工作表</th>
              <th>狀態</th>
              <th>列數</th>
            </tr>
          </thead>
          <tbody>
            {% for report in reports[:12] %}
              <tr>
                <td>{{ report.file_name }}</td>
                <td>{{ report.sheet_name }}</td>
                <td>{{ "已讀" if report.status == "loaded" else report.reason }}</td>
                <td>{{ report.rows }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      {% endif %}
    </section>
  </main>
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

    if action == "stats":
        try:
            rules, rule_stats = generate_ng_rules(result.dataframe)
        except Exception as exc:
            return render_page(error=f"建立統計資料失敗：{exc}", result=result)

        stats_name = f"NG項_最終維修建議對照_{timestamp}.csv"
        stats_path = output_path_for(stats_name)
        rules.to_csv(stats_path, index=False, encoding="utf-8-sig")
        write_shared_rules_csv(rules)
        return render_page(result=result, stats_file=stats_name, rule_stats=rule_stats.as_dict(), mode="dataset")

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
    upload = request.files.get("rules_file")
    if upload is None or not upload.filename:
        return render_page(error="請選擇 NG項_最終維修建議對照.csv", mode="csv_train")

    try:
        content = upload.read()
        rules = read_rules_csv(content)
        training = train_rf_mcpr(rules, model_path=shared_model_path())
    except Exception as exc:
        return render_page(error=f"用 CSV 訓練 RF-MCPR 失敗：{exc}", mode="csv_train")

    write_shared_rules_csv(rules)

    rule_stats = {
        "output_rows": int(len(rules)),
        "unique_ng_items": int(rules["NG項"].nunique()) if "NG項" in rules else 0,
        "unique_repairs": int(rules["維修建議"].nunique()) if "維修建議" in rules else 0,
        "groups_with_pass": int(rules["異常編號"].nunique()) if "異常編號" in rules else 0,
    }
    return render_page(rule_stats=rule_stats, training=training, mode="csv_train")


def render_page(
    error: str = "",
    result=None,
    output_file: str = "",
    stats_file: str = "",
    rule_stats: dict[str, int] | None = None,
    training=None,
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
        rule_stats=rule_stats,
        training=training,
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
