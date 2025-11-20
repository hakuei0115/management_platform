<template>
  <el-card class="operation-page">
    <!-- 查詢區 -->
    <div class="toolbar">
      <el-form :inline="true" :model="filters" class="qform">
        <el-form-item label="起始序號">
          <el-input v-model="filters.start_id" type="number" placeholder="輸入序號" style="width:120px" />
        </el-form-item>

        <el-form-item label="結束序號">
          <el-input v-model="filters.end_id" type="number" placeholder="輸入序號" style="width:120px" />
        </el-form-item>

        <el-form-item label="產品規格">
          <el-input v-model="filters.product_spec" placeholder="例如 MAFR-302" style="width:120px" />
        </el-form-item>

        <el-form-item label="生產時段">
          <el-date-picker v-model="filters.range" type="datetimerange" range-separator="至" start-placeholder="開始"
            end-placeholder="結束" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="applyFilter">查詢</el-button>
          <el-button type="warning" plain @click="showOnlyNG">只看NG</el-button>
          <el-button @click="resetFilter">重置</el-button>
          <el-button type="success" @click="exportExcel">匯出 Excel</el-button>
        </el-form-item>

        <el-popover trigger="click" placement="bottom-end" width="260">
          <template #reference>
            <el-button icon="el-icon-setting">欄位設定</el-button>
          </template>

          <div style="display: flex; gap: 6px; margin-bottom: 8px;">
            <el-button size="small" type="primary" plain @click="selectAllColumns">全選</el-button>
            <el-button size="small" type="danger" plain @click="clearAllColumns">全取消</el-button>
          </div>

          <el-checkbox-group v-model="visibleColumns" class="col-setting">
            <el-checkbox v-for="col in allColumns" :key="col.prop" :label="col.prop">
              {{ col.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-popover>
      </el-form>
    </div>

    <!-- 資料表 -->
    <el-table :data="rows" border height="70vh">
      <el-table-column prop="id" label="序號" width="80" />

      <el-table-column v-if="visibleColumns.includes('timestamp')" prop="timestamp" label="時間" width="180">
        <template #default="{ row }">
          {{ formatTime(row.timestamp) }}
        </template>
      </el-table-column>
      <el-table-column v-if="visibleColumns.includes('station_no')" prop="station_no" label="站點" width="100" />
      <el-table-column v-if="visibleColumns.includes('product_spec')" prop="product_spec" label="產品規格" width="120" />

      <!-- NG 項 -->
      <el-table-column label="NG 項" width="160">
        <template #default="{ row }">
          <span v-if="row.ng_items.length">
            <el-tag v-for="item in row.ng_items" :key="item" type="danger" size="small">{{ item }}</el-tag>
          </span>
          <span v-else>
            <el-tag type="success" size="small">OK</el-tag>
          </span>
        </template>
      </el-table-column>

      <!-- 12 個測試欄 -->
      <el-table-column v-for="col in visibleTestColumns" :key="col.prop" :prop="col.prop" :label="col.label"
        width="200">
        <template #default="{ row }">
          <el-tag v-if="row[col.prop].includes('不測試') || row[col.prop].includes('未測試')" type="info">{{ row[col.prop]
          }}</el-tag>
          <el-tag v-else-if="row[col.prop].includes('NG')" type="danger">{{ row[col.prop] }}</el-tag>
          <el-tag v-else type="success">{{ row[col.prop] }}</el-tag>
        </template>
      </el-table-column>

      <!-- 洩漏量欄位 -->
      <el-table-column v-for="col in visibleLeakColumns" :key="col.prop" :prop="col.prop" :label="col.label"
        width="180" />

      <!-- 維修建議與可能部位 -->
      <el-table-column label="維修建議" prop="suggestion" width="160">
        <template #default="{ row }">
          <div v-html="formatSuggestion(row.suggestion)"></div>
        </template>
      </el-table-column>

      <el-table-column label="可能部位" prop="part" width="140" />
    </el-table>

    <!-- 分頁 -->
    <div style="text-align:center; margin-top:12px;">
      <el-pagination background layout="prev, pager, next, sizes, total" :total="total" :current-page="currentPage"
        :page-size="pageSize" @current-change="handlePageChange" @size-change="handleSizeChange"
        :page-sizes="[10, 20, 50, 100]" />
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useEquipmentDataStore } from '@/stores/equipmentData'
import { useModelPredictStore } from '@/stores/modelPredict'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'

const equipmentDataStore = useEquipmentDataStore()
const modelPredictStore = useModelPredictStore()

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const rows = ref([])
let timer = null

function formatSuggestion(text) {
  if (!text) return ''
  return text.split(',').join('<br>')
}

const triggerByFilter = ref(false)
const filters = ref({
  start_id: '',
  end_id: '',
  product_spec: '',
  range: [],
  only_ng: false,
})

function formatTime(isoString) {
  return dayjs(isoString).format('YYYY-MM-DD HH:mm:ss')
}

function extractNgItems(record) {
  const checks = ['m01', 'm02', 'm03', 'm04', 'm05', 'm06', 'm07', 'm08', 'm09', 'm10', 'm11', 'm12']
  const ng = []

  for (const key of checks) {
    if (record[key]?.includes('NG')) {
      ng.push(key)
    }
  }
  return ng
}

function mapRecord(r) {
  return {
    timestamp: r.time,

    id: r.serial_no,
    station_no: r.station,
    product_spec: r.recipe_channel,

    M01: r.m01,
    M02: r.m02,
    M03: r.m03,
    M04: r.m04,
    M05: r.m05,
    M06: r.m06,
    M07: r.m07,
    M08: r.m08,
    M09: r.m09,
    M10: r.m10,
    M11: r.m11,
    M12: r.m12,

    M04_leak: r.M04?.leak,
    M05_leak: r.M05?.leak,
    M08_leak: r.M08?.leak,
    M11_leak: r.M11?.leak,

    ng_items: extractNgItems(r),

    suggestion: '',
    part: '',
  }
}

async function fetchOperations() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      start_id: filters.value.start_id || '',
      end_id: filters.value.end_id || '',
      product_spec: filters.value.product_spec || '',
      only_ng: filters.value.only_ng || false,
    }

    if (filters.value.range?.length === 2) {
      params.start_time = filters.value.range[0]
      params.end_time = filters.value.range[1]
    }

    // 後端拿資料
    await equipmentDataStore.fetchEquipmentData(params)

    const result = equipmentDataStore.equipmentDataList
    total.value = result.total

    // 資料映射
    rows.value = result.records.map(mapRecord)

    await Promise.all(
      rows.value.map(async (row) => {
        if (!row.ng_items || row.ng_items.length === 0) {
          row.suggestion = '產品狀態良好，無需維修'
          row.part = '無'
          return
        }

        await modelPredictStore.predictModel(row.ng_items)
        row.suggestion = modelPredictStore.predictionResult.suggestions
        row.part = modelPredictStore.predictionResult.parts
      })
    )
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  triggerByFilter.value = true
  currentPage.value = 1
  fetchOperations()
}

async function showOnlyNG() {
  filters.value.only_ng = true
  currentPage.value = 1
  await fetchOperations()
}

function resetFilter() {
  filters.value = {
    start_id: '',
    end_id: '',
    product_spec: '',
    range: [],
    only_ng: false,
  }
  currentPage.value = 1
  fetchOperations()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchOperations()
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchOperations()
}

onMounted(() => {
  fetchOperations()
  timer = setInterval(fetchOperations, 10 * 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

const testColumns = [
  { prop: 'M01', label: 'M01_低壓手動排水閥測試_測試結果' },
  { prop: 'M02', label: 'M02_高壓手動排水閥測試_測試結果' },
  { prop: 'M03', label: 'M03_低壓內漏調壓_測試結果' },
  { prop: 'M04', label: 'M04_低壓內漏測試_測試結果' },
  { prop: 'M05', label: 'M05_高壓內漏測試_測試結果' },
  { prop: 'M06', label: 'M06_低壓氣密調壓_測試結果' },
  { prop: 'M07', label: 'M07_低壓錶孔測試_測試結果' },
  { prop: 'M08', label: 'M08_低壓氣密測試_測試結果' },
  { prop: 'M09', label: 'M09_高壓氣密調壓_測試結果' },
  { prop: 'M10', label: 'M10_高壓錶孔測試_測試結果' },
  { prop: 'M11', label: 'M11_高壓氣密測試_測試結果' },
  { prop: 'M12', label: 'M12_測試完成調壓_測試結果' },
]

const leakColumns = [
  { prop: 'M04_leak', label: 'M04_低壓內漏測試_洩漏量' },
  { prop: 'M05_leak', label: 'M05_高壓內漏測試_洩漏量' },
  { prop: 'M08_leak', label: 'M08_低壓氣密測試_洩漏量' },
  { prop: 'M11_leak', label: 'M11_高壓氣密測試_洩漏量' },
]

const allColumns = [
  { prop: 'timestamp', label: '時間' },
  { prop: 'station_no', label: '站點' },
  { prop: 'product_spec', label: '產品規格' },
  ...testColumns,
  ...leakColumns,
]

const visibleColumns = ref(allColumns.map(c => c.prop))

const visibleTestColumns = computed(() =>
  testColumns.filter(col => visibleColumns.value.includes(col.prop))
)
const visibleLeakColumns = computed(() =>
  leakColumns.filter(col => visibleColumns.value.includes(col.prop))
)

function selectAllColumns() {
  visibleColumns.value = allColumns.map(c => c.prop)
}

function clearAllColumns() {
  visibleColumns.value = []
}

function exportExcel() {
  if (!rows.value.length) {
    ElMessage.warning("沒有可匯出的資料")
    return
  }

  const exportData = rows.value.map(row => ({
    序號: row.id,
    時間: formatTime(row.timestamp),
    站點: row.station_no,
    產品規格: row.product_spec,
    NG項: row.ng_items.join(', ') || 'OK',
    ...Object.fromEntries(
      Object.keys(row)
        .filter(k => k.startsWith("M") && k.length === 3) // M01 ~ M12
        .map(k => [k + "_測試結果", row[k]])
    ),
    ...Object.fromEntries(
      Object.keys(row)
        .filter(k => k.endsWith("_leak"))
        .map(k => [k, row[k]])
    ),
    維修建議: row.suggestion,
    可能部位: row.part,
  }))

  const worksheet = XLSX.utils.json_to_sheet(exportData)

  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, "資料列表")

  const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" })
  saveAs(new Blob([excelBuffer]), `${dayjs().format("YYYYMMDD_HHmmss")}.xlsx`)
}
</script>

<style scoped>
.operation-page {
  font-size: 15px;
}

.qform {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: flex-end;
}

.col-setting {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
