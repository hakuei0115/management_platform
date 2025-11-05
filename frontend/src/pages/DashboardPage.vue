<template>
    <el-card class="dashboard-page">
        <!-- 🔹 上半：動態區塊 -->
        <div class="section-title">最新數據（自動更新）</div>
        <el-table :data="latestRows" border height="300">
            <el-table-column prop="id" label="序號" width="100" />
            <el-table-column prop="station_no" label="站點" width="100" />
            <el-table-column prop="product_spec" label="產品型號" width="160" />
            <el-table-column prop="suggestion" label="維修建議" width="200" />
            <el-table-column prop="part" label="可能部位" width="160" />
        </el-table>

        <!-- 🔹 下半：靜態查詢區 -->
        <div class="section-title" style="margin-top:20px;">查詢歷史紀錄</div>
        <el-form :inline="true" :model="filters" class="qform">
            <el-form-item label="序號">
                <el-input v-model="filters.id" placeholder="輸入序號" style="width:120px" />
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
            <el-table-column prop="station_no" label="站點" width="100" />
            <el-table-column prop="product_spec" label="產品型號" width="160" />
            <el-table-column prop="suggestion" label="維修建議" width="200" />
            <el-table-column prop="part" label="可能部位" width="160" />
        </el-table>
    </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
// import { getLatestData, getFilteredData } from '@/services/api' // 將來接API用

// ------------------ 假資料 ------------------
const allData = ref([
    { id: 1087, station_no: 3, product_spec: 'MAFR-302', suggestion: '吹淨帽型蓋', part: '帽型蓋' },
    { id: 1088, station_no: 4, product_spec: 'MAFR-302', suggestion: '更換氣閥', part: '氣閥' },
    { id: 1089, station_no: 2, product_spec: 'MAFR-302', suggestion: '檢查活塞密封', part: '活塞' },
])

// 🔹 最新數據（會自動刷新）
const latestRows = ref([])

function fetchLatest() {
    // const res = await getLatestData()
    // latestRows.value = res.data
    latestRows.value = allData.value.slice(-5).reverse() // 假：取最新五筆
    console.log('更新最新資料')
}

let timer = null
onMounted(() => {
    fetchLatest()
    timer = setInterval(fetchLatest, 10000) // 每10秒自動更新
})
onUnmounted(() => clearInterval(timer))

// 🔹 查詢功能
const filters = ref({ id: '', product_spec: '', range: [] })
const filteredRows = computed(() => {
    return allData.value.filter(r => {
        const matchId = filters.value.id ? String(r.id) === String(filters.value.id) : true
        const matchSpec = filters.value.product_spec
            ? r.product_spec.toLowerCase().includes(filters.value.product_spec.toLowerCase())
            : true
        return matchId && matchSpec
    })
})

function applyFilter() {
    ElMessage.success('已套用篩選條件')
}
function resetFilter() {
    filters.value = { id: '', product_spec: '', range: [] }
}
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
