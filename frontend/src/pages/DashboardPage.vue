<template>
    <el-card class="dashboard-page">

        <!-- 查詢區 -->
        <div class="section-title">數據查詢與即時更新</div>
        <el-form :inline="true" :model="filters" class="qform">
            <el-form-item label="起始序號">
                <el-input v-model="filters.start_id" type="number" placeholder="序號" style="width:120px" />
            </el-form-item>

            <el-form-item label="結束序號">
                <el-input v-model="filters.end_id" type="number" placeholder="序號" style="width:120px" />
            </el-form-item>

            <el-form-item label="產品型號">
                <el-input v-model="filters.product_spec" placeholder="例如 MAFR-302" style="width:160px" />
            </el-form-item>

            <el-form-item label="生產時段">
                <el-date-picker
                    v-model="filters.range"
                    type="datetimerange"
                    range-separator="至"
                    start-placeholder="開始"
                    end-placeholder="結束"
                />
            </el-form-item>

            <el-form-item>
                <el-button type="primary" @click="applyFilter">查詢</el-button>
                <el-button @click="resetFilter">重置</el-button>
            </el-form-item>
        </el-form>

        <!-- 主表格（僅 50 筆 FIFO） -->
        <el-table :data="rows" border stripe height="70vh" :loading="loading" row-class-name="tableRowClass">
            <el-table-column prop="id" label="序號" width="100" />
            <el-table-column prop="timestamp" label="時間" width="180">
                <template #default="{ row }">
                    {{ formatTime(row.timestamp) }}
                </template>
            </el-table-column>
            <el-table-column prop="station_no" label="站點" width="100" />
            <el-table-column prop="product_spec" label="產品型號" width="160" />

            <el-table-column label="NG 項" width="160">
                <template #default="{ row }">
                    <el-tag v-for="item in row.ng_items" :key="item" size="small" type="danger">{{ item }}</el-tag>
                    <el-tag v-if="row.ng_items.length === 0" size="small" type="success">OK</el-tag>
                </template>
            </el-table-column>

            <el-table-column label="維修建議">
                <template #default="{ row }">
                    <div v-html="formatSuggestion(row.suggestion)" />
                </template>
            </el-table-column>

            <el-table-column prop="part" label="可能部位" />
        </el-table>

    </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useEquipmentDataStore } from '@/stores/equipmentData'
import { useModelPredictStore } from '@/stores/modelPredict'
import dayjs from 'dayjs'

const equipmentDataStore = useEquipmentDataStore()
const modelPredictStore = useModelPredictStore()

const loading = ref(false)
const rows = ref([])   // ★ 只存 50 筆資料（FIFO）

let timer = null

const filters = ref({
    start_id: "",
    end_id: "",
    product_spec: "",
    range: [],
})

function formatTime(t) {
    return dayjs(t).format("YYYY-MM-DD HH:mm:ss")
}

function formatSuggestion(s) {
    if (!s) return ""
    return s.split(",").join("<br>")
}

function extractNgItems(r) {
    const checks = ["m01","m02","m03","m04","m05","m06","m07","m08","m09","m10","m11","m12"]
    return checks.filter(k => r[k]?.includes("NG"))
}

function mapRecord(r) {
    return {
        timestamp: r.time,
        id: r.serial_no,
        station_no: r.station,
        product_spec: r.recipe_channel,
        ng_items: extractNgItems(r),
        suggestion: "",
        part: "",
    }
}

/** ⭐ 從 API 拉資料（三種情況都共用這個 function）*/
async function fetchData(appendMode = false) {
    loading.value = true

    const params = { ...filters.value }

    if (filters.value.range.length === 2) {
        params.start_time = dayjs(filters.value.range[0]).format("YYYY-MM-DD HH:mm:ss")
        params.end_time = dayjs(filters.value.range[1]).format("YYYY-MM-DD HH:mm:ss")
    }

    await equipmentDataStore.fetchEquipmentData(params)

    const mapped = equipmentDataStore.equipmentDataList.records.map(mapRecord)

    await Promise.all(
        mapped.map(async (row) => {
            if (row.ng_items.length === 0) {
                row.suggestion = "產品狀態良好，無需維修"
                row.part = "無"
            } else {
                await modelPredictStore.predictModel(row.ng_items)
                row.suggestion = modelPredictStore.predictionResult.suggestions
                row.part = modelPredictStore.predictionResult.parts
            }
        })
    )

    if (!appendMode) {
        rows.value = mapped.slice(-50)
    } else {
        for (const r of mapped) {
            rows.value.push(r)
            if (rows.value.length > 50) rows.value.shift()  // ★ FIFO
        }
    }

    loading.value = false
}

async function applyFilter() {
    rows.value = []
    await fetchData(false)
}

function resetFilter() {
    filters.value = {
        start_id: "",
        end_id: "",
        product_spec: "",
        range: [],
    }
    rows.value = []
    fetchData(false)
}

/** ⭐ 定時更新：每 10 秒拉一次新資料，採 FIFO */
async function tick() {
    console.log("⏱ 自動刷新資料...")

    // 若沒有資料 → 直接重新查詢一次
    if (rows.value.length === 0) {
        await fetchData(false)
        return
    }

    // 抓最後一筆時間
    const lastTime = rows.value[rows.value.length - 1].timestamp

    filters.value.range = [
        dayjs(lastTime),
        dayjs(),
    ]

    await fetchData(true) // append mode
}

onMounted(() => {
    fetchData(false)
    timer = setInterval(tick, 10 * 1000)
})
onUnmounted(() => clearInterval(timer))
</script>


<style scoped>
.dashboard-page {
    font-size: 15px;
}

.section-title {
    font-weight: bold;
    margin-bottom: 8px;
    font-size: 16px;
}

.qform {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: flex-end;
}

:deep(.el-table thead th) {
    background-color: #687480;
    color: #e3e7ec;
    font-weight: bold;
}
</style>
