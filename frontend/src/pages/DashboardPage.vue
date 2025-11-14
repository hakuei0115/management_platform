<template>
    <el-card class="dashboard-page">
        <!-- 🔹 上半：動態區塊 -->
        <div class="section-title">最新數據（自動更新）</div>
        <el-table :data="latestRows" border height="300">
            <el-table-column prop="id" label="序號" width="100" />
            <el-table-column prop="timestamp" label="時間" width="180" >
                <template #default="{ row }">
                    {{ formatTime(row.timestamp) }}
                </template>
            </el-table-column>
            <el-table-column prop="station_no" label="站點" width="100" />
            <el-table-column prop="product_spec" label="產品型號" width="160" />
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
            <el-table-column prop="suggestion" label="維修建議" />
            <el-table-column prop="part" label="可能部位" />
        </el-table>

        <!-- 🔹 下半：靜態查詢區 -->
        <div class="section-title" style="margin-top:20px;">查詢歷史紀錄</div>
        <el-form :inline="true" :model="filters" class="qform">
            <el-form-item label="起始序號">
                <el-input v-model="filters.start_id" type="number" placeholder="輸入序號" style="width:120px" />
            </el-form-item>

            <el-form-item label="結束序號">
                <el-input v-model="filters.end_id" type="number" placeholder="輸入序號" style="width:120px" />
            </el-form-item>
            <el-form-item label="產品型號">
                <el-input v-model="filters.product_spec" placeholder="例如 MAFR-302" style="width:160px" />
            </el-form-item>
            <el-form-item label="生產時段">
                <el-date-picker v-model="filters.range" type="datetimerange" range-separator="至" start-placeholder="開始"
                    end-placeholder="結束" />
            </el-form-item>
            <el-form-item>
                <el-button type="primary" @click="applyFilter">查詢</el-button>
                <el-button @click="resetFilter">重置</el-button>
            </el-form-item>
        </el-form>

        <el-table :data="filteredRows" border height="360" style="margin-top:8px;">
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
                    <span v-if="row.ng_items.length">
                        <el-tag v-for="item in row.ng_items" :key="item" type="danger" size="small">{{ item }}</el-tag>
                    </span>
                    <span v-else>
                        <el-tag type="success" size="small">OK</el-tag>
                    </span>
                </template>
            </el-table-column>
            <el-table-column prop="suggestion" label="維修建議" />
            <el-table-column prop="part" label="可能部位" />
        </el-table>
    </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useEquipmentDataStore } from '@/stores/equipmentData'
import { useModelPredictStore } from '@/stores/modelPredict'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.tz.setDefault('Asia/Taipei')

const equipmentDataStore = useEquipmentDataStore()
const modelPredictStore = useModelPredictStore()

const latestLoading = ref(false)
const searchLoading = ref(false)

const latestRows = ref([])
const filteredRows = ref([])

// timer for periodic fetchLatest interval
let timer = null

const filters = ref({
    start_id: '',
    end_id: '',
    product_spec: '',
    range: [],
})

function formatTime(isoString) {
    if (!isoString) return ''
    return dayjs.utc(isoString).tz('Asia/Taipei').format('YYYY-MM-DD HH:mm:ss')
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

async function fetchLatest() {
    latestLoading.value = true
    try {
        const now = dayjs()
        const fiveMinAgo = dayjs().subtract(5, 'minute')

        const params = {
            page: 1,
            pageSize: 20,
            start_time: fiveMinAgo.format('YYYY-MM-DD HH:mm:ss'),
            end_time: now.format('YYYY-MM-DD HH:mm:ss'),
        }

        await equipmentDataStore.fetchEquipmentData(params)

        let records = equipmentDataStore.equipmentDataList.records

        // mapping
        const mapped = records.map(mapRecord)

        // 平行預測
        await Promise.all(
            mapped.map(async (row) => {
                if (!row.ng_items.length) {
                    row.suggestion = '產品狀態良好，無需維修'
                    row.part = '無'
                    return
                }

                await modelPredictStore.predictModel(row.ng_items)
                row.suggestion = modelPredictStore.predictionResult.suggestions
                row.part = modelPredictStore.predictionResult.parts
            })
        )

        latestRows.value = mapped
    } finally {
        latestLoading.value = false
    }
}

async function applyFilter() {
    searchLoading.value = true
    try {
        const params = {
            start_id: filters.value.start_id,
            end_id: filters.value.end_id,
            product_spec: filters.value.product_spec,
        }

        if (filters.value.range.length === 2) {
            params.start_time = dayjs(filters.value.range[0]).format('YYYY-MM-DD HH:mm:ss')
            params.end_time = dayjs(filters.value.range[1]).format('YYYY-MM-DD HH:mm:ss')
        }

        await equipmentDataStore.fetchEquipmentData(params)

        let mapped = equipmentDataStore.equipmentDataList.records.map(mapRecord)

        await Promise.all(
            mapped.map(async (row) => {
                if (!row.ng_items.length) {
                    row.suggestion = '產品狀態良好，無需維修'
                    row.part = '無'
                    return
                }

                await modelPredictStore.predictModel(row.ng_items)
                row.suggestion = modelPredictStore.predictionResult.suggestions
                row.part = modelPredictStore.predictionResult.parts
            })
        )

        filteredRows.value = mapped
    } finally {
        searchLoading.value = false
    }
}


function resetFilter() {
    filters.value = {
        start_id: '',
        end_id: '',
        product_spec: '',
        range: [],
    }
}

// 每五分鐘更新一次
onMounted(() => {
    fetchLatest()
    timer = setInterval(fetchLatest, 5 * 60 * 1000)
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
</style>
