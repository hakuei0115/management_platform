# 智能數據管理平台（Vue 3）README

這份 README 說明整個專案架構、每個資料夾與檔案的用途，讓開發者能快速理解專案組成並進行維護或擴充。

---

## 📁 專案結構總覽

```
smart-leakage-platform/
├─ index.html                # 入口 HTML（由 Vite 掛載 Vue app）
├─ package.json              # 專案設定與依賴套件
├─ vite.config.js            # Vite 組態設定（可調整代理、HMR 等）
└─ src/                      # 主程式目錄
   ├─ main.js                # Vue 進入點，掛載 App.vue
   ├─ App.vue                # 主版面（包含側邊選單與 <router-view>）
   ├─ router/                # 前端路由設定
   │   └─ index.js           # 定義三大頁面路由
   ├─ stores/                # 全域狀態管理（Pinia）
   │   ├─ equipment.js       # 管理設備管理頁面的資料狀態
   │   └─ query.js           # 管理操作管理頁面的查詢條件與結果
   ├─ services/              # API 存取模組
   │   └─ api.js             # 統一封裝 axios API 請求（Device / Operation / Quality）
   ├─ pages/                 # 三大主要功能頁面
   │   ├─ EquipmentPage.vue  # 設備管理頁面（CRUD + 站點查看）
   │   ├─ OperationPage.vue  # 操作管理頁面（查詢與結果表格）
   │   └─ QualityPage.vue    # 品質分析頁面（圖表與異常分析）
   ├─ components/            # 可重用元件
   │   ├─ EquipmentForm.vue     # 新增 / 編輯設備表單
   │   ├─ StationTable.vue      # 顯示設備下站點資訊
   │   ├─ DataQueryForm.vue     # 操作管理的查詢表單
   │   ├─ RecordTable.vue       # 顯示查詢結果的表格
   │   ├─ QualityOverview.vue   # 品質分析總覽圖表（ECharts）
   │   ├─ AnomalyCauseList.vue  # 顯示異常原因與可能部位
   │   └─ SuggestionCards.vue   # 顯示改善建議卡片
   ├─ assets/                # 靜態資源（圖示、logo、圖片等）
   └─ styles/                # 樣式設定
       └─ variables.css      # 共用樣式變數（顏色、間距等）
```

---

## 🚀 啟動方式

### 1. 安裝依賴
```bash
npm install
```

### 2. 啟動開發伺服器
```bash
npm run dev
```
→ 打開瀏覽器後可看到「智能數據管理平台」主畫面。

### 3. 打包部署
```bash
npm run build
```
輸出結果會在 `dist/` 資料夾。

---

## 🧩 主要功能說明

### 🛠️ 設備管理（EquipmentPage）
- 顯示所有氣密檢測設備列表。
- 可新增、編輯、刪除設備。
- 查看每台設備底下的測試站（1~4）。
- 站點狀態可切換啟用 / 停用。

對應 API：`/api/devices`, `/api/devices/:id/stations`

### ⚙️ 操作管理（OperationPage）
- 從資料庫查詢測試參數（壓力、洩漏值、調壓值等）。
- 查詢條件包含產品規格、時間範圍、設備、站點等。
- 查詢結果支援分頁、排序、CSV 匯出。

對應 API：`/api/operations/records`, `/api/operations/export`

### 📊 品質分析（QualityPage）
- 以圖表顯示測試結果統計（異常比例、趨勢）。
- 顯示品質異常原因與可能部位。
- 根據規則 / 統計提供重工或更換建議。

對應 API：`/api/quality/overview`, `/api/quality/anomalies`, `/api/quality/suggestions`

---

## 🧠 資料流與狀態
- Vue Router 控制頁面切換。
- Pinia store（equipment / query）維持查詢狀態與結果。
- Axios 負責與後端 API 溝通，所有請求封裝在 `services/api.js`。
- 元件之間透過 `props` 與 `emit` 溝通（例如表單送出後重新載入列表）。

---

## ⚡ 效能策略
1. **分頁查詢**：後端需支援 `page`、`pageSize`，避免一次回傳大量資料。
2. **必要條件查詢**：查詢前需選擇產品規格與時段，減少無效查詢。
3. **前端節流**：防止重複送出查詢請求。
4. **延遲載入**：頁面以 lazy load (`import()` 語法) 載入，提升首屏速度。
5. **圖表抽樣**：品質分析頁面以聚合或抽樣資料顯示，避免效能瓶頸。

---

## 🎨 UI / UX 設計重點
- 使用 **Element Plus** 元件庫，風格統一、相容性佳。
- 側邊選單 + Header 結構清晰。
- 表格與圖表並列呈現，資訊層次分明。
- 支援 RWD（彈性布局、grid / flex）。

---

## 🧰 可擴充功能建議
- 權限管理（不同角色對應不同頁面與操作）。
- WebSocket / SSE 即時監控設備狀態。
- 匯出報表（CSV / Excel / PDF）。
- 統計分析與 ML 模型接入（自動預測異常）。

---

## 👨‍💻 開發建議
1. 若要對接後端，可在 `vite.config.js` 增加代理：
```js
server: {
  proxy: {
    '/api': 'http://localhost:5000'
  }
}
```
2. 若無後端可先用 Mock：
```bash
npm i vite-plugin-mock -D
```
3. 保持檔案命名一致（區分大小寫），否則 Vite 可能報錯「Failed to resolve import」。

---

📄 **結語**
本專案為一套可直接落地的 Vue 3 智能數據管理平台框架，模組化程度高、便於擴充。  
可依據實際氣密檢測資料庫結構，快速串接 API 與強化 UI 視覺呈現。

