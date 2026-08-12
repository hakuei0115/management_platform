# 🏭 智能維修推薦與產線管理平台 (Smart Maintenance Recommendation & Manufacturing Management Platform)

本平台整合產線檢測資料管理、三階段 AI 故障診斷引擎 (Open-Set + RF-MCPR + ADMDP) 與微服務架構，提供即時維修建議推薦與動態診斷追蹤。

---

## 🌟 系統核心亮點

### 1. 三聯動 AI 協同診斷管線 (3-Tier Synergistic AI Pipeline)
- 🛡️ **第一階段：Open-Set 開集識別 (防衛門衛)**
  - 利用極值理論 (Extreme Value Theory, EVT) 進行異常組合邊界校驗。
  - 當產線出現未曾見過的全新 NG 組合時，自動阻斷並警示「未知異常組合」，避免模型盲目預測。
- 🟢 **第二階段：RF-MCPR 主模型初診 (Top-1 靜態診斷)**
  - 通過開集識別後，由隨機森林多類別預測模型 (RF-MCPR) 輸出**機率最高之 Top-1 單一維修建議**，確保第一次維修決策明確且可追蹤。
- 🔄 **第三階段：ADMDP 吸收馬可夫動態複診 (站點動態追蹤)**
  - 若第一次維修後依然 NG，系統自動切換至 **ADMDP 吸收馬可夫決策鏈** 進行動態追蹤。
  - 根據站點紀錄與洩漏量趨勢變化（$\Delta \text{leakage}$：`worse` / `improved` / `same`），提供最佳化二次維修策略。
  - 產品測試 PASS 時自動清理站點 Session，完成結案。

### 2. 站點級 Session 管理 (Station-based Repair Tracking)
- 針對產線實務「同站點重複檢測與維修」情境，以 `station_id` 自動維持維修 Session，解決序號與歷程關聯難題。
- 基於 **Redis 記憶體快取** (TTL=7200s)，高效儲存二次診斷所需的洩漏量趨勢與前次處置動作。

### 3. 一體化 Web 訓練平台 (Training Web GUI)
- 提供獨立的 Web 訓練介面 (Port 8501)，具備**兩步驟流暢工作流**與**全螢幕動態等待遮罩**：
  - **步驟 1：資料集生成**（自動合併 Excel 並產出 `NG對照表.csv`、`ADMDP轉移鏈.csv` 與 `merged_train_data.xlsx`）。
  - **步驟 2：AI 模型訓練**（支援「🚀 一鍵訓練全套 AI 模型」與「獨立單獨訓練」）。

---

## 🏗️ 系統微服務架構 (Architecture)

```
                     ┌────────────────────────────────────────┐
                     │          Web 瀏覽器 / 前端 App          │
                     └───────────────────┬────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                 前端服務 (Port 80)             訓練平台 GUI (Port 8501)
               [Vue 3 + Vite + G2]               [Flask + Pure CSS]
                         │                               │
       ┌─────────────────┴─────────────────┐             │
       ▼                                   ▼             ▼
後端 API (Port 3000)             實時推論引擎 (Port 5001) ───┤ 共享模型權重與資料
[Node.js + Express]              [Flask + Py3.9 + Scikit]  │ (/shared/model_predict)
       │                                   │             │
       ▼                                   ▼             │
 MariaDB (Port 3306)              Redis (Port 6379) ─────┘
[檢測/規格/權限資料]              [站點 Session 快取]
```

| 微服務名稱 | 服務說明 | 運行埠號 (Port) | 主要技術棧 |
| :--- | :--- | :--- | :--- |
| `frontend` | 產線管理與維修推薦前端 | `http://localhost:80` | Vue 3, Vite, Element Plus, AntV G2 |
| `backend` | 業務邏輯與權限管理 API | `http://localhost:3000` | Node.js, Express, JWT, Sequelize |
| `model` (`mp_model`) | AI 實時推論 API 引擎 | `http://localhost:5001` | Python 3.9, Flask, Scikit-learn |
| `train_model` (`mp_train_model`) | 多模型一體化訓練 Web GUI | `http://localhost:8501` | Python 3.9, Flask, Pandas, Pure CSS |
| `mariadb` | 關聯式資料庫 | `localhost:3306` | MariaDB 10.6 |
| `redis` | 站點 Session 記憶體快取 | `localhost:6379` | Redis 7.0 |

---

## 🚀 快速啟動與部署 (Getting Started)

### 前置需求
- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)

### 1. 複製專案與啟動服務
```bash
git clone <repository-url>
cd management_platform

# 一鍵啟動全套微服務 (MariaDB, Redis, Backend, Model, Train, Frontend)
docker compose -f docker-compose-dev.yaml up -d --build
```

### 2. 存取入口
- **產線管理前端**：`http://localhost`
- **模型訓練 GUI**：`http://localhost:8501`
- **AI 推論 API 測試**：`http://localhost:5001/predict`

---

## 📖 AI 診斷 API 使用說明

### 請求端點：`POST http://localhost:5001/predict`

#### 範例 1：初次診斷 (Stage 1 - Top-1 RF-MCPR)
**Request Body:**
```json
{
  "station_id": "STATION_01",
  "ng_items": ["M04_低壓內漏測試_洩漏量_NG"],
  "leak_values": {
    "M04_低壓內漏測試_洩漏量": 4.5
  }
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "stage": "STAGE_1_RF_MCPR",
    "open_set_status": "CONFIDENT",
    "suggestions": ["DS環脫落"],
    "attempt_count": 1
  }
}
```

#### 範例 2：同站點二次複診 (Stage 2 - ADMDP 依趨勢動態推薦)
**Request Body:**
```json
{
  "station_id": "STATION_01",
  "ng_items": ["M04_低壓內漏測試_洩漏量_NG"],
  "leak_values": {
    "M04_低壓內漏測試_洩漏量": 6.8
  }
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "stage": "STAGE_2_ADMDP",
    "open_set_status": "CONFIDENT",
    "suggestions": ["更換活塞"],
    "attempt_count": 2,
    "leak_trend": "worse"
  }
}
```

#### 範例 3：產品測試 PASS (自動關閉站點 Session)
**Request Body:**
```json
{
  "station_id": "STATION_01",
  "ng_items": [],
  "leak_values": {}
}
```
**Response:**
```json
{
  "success": true,
  "data": {
    "stage": "PASS",
    "suggestions": "產品測試 PASS，站點維修 Session 結案關閉"
  }
}
```

---

## 🛠️ 專案目錄結構

```
management_platform/
├── model_predict/          # AI 推論 API 微服務 (Port 5001)
│   ├── app.py              # Flask 核心控制器與 3-Tier 診斷邏輯
│   ├── open_set_rf_prediction.py
│   ├── admdp_prediction.py
│   └── Dockerfile
├── train_model/            # 一體化訓練 Web GUI (Port 8501)
│   ├── merge_gui.py        # 訓練 GUI 核心與路由
│   ├── generate_ng_rules.py# NG 對照表提取
│   ├── admdp_dataset.py    # ADMDP 狀態轉移鏈資料集生成
│   └── admdp_training.py   # ADMDP Policy 訓練引擎
├── backend/                # Node.js 後端服務 (Port 3000)
├── frontend/               # Vue 3 前端服務 (Port 80)
└── docker-compose-dev.yaml # Docker Compose 容器編排
```

---

## 📄 授權說明
本專案基於 MIT 授權條款釋出。
