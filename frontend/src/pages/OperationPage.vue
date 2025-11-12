<template>
    <el-card class="operation-page">
        <!-- 查詢區 -->
        <div class="toolbar">
            <el-form :inline="true" :model="filters" class="qform">
                <el-form-item label="序號">
                    <el-input v-model="filters.id" placeholder="輸入序號" style="width:120px" />
                </el-form-item>

                <el-form-item label="產品規格">
                    <el-input v-model="filters.product_spec" placeholder="例如 MAFR-302" style="width:180px" />
                </el-form-item>

                <el-form-item label="生產時段">
                    <el-date-picker v-model="filters.range" type="datetimerange" range-separator="至"
                        start-placeholder="開始" end-placeholder="結束" />
                </el-form-item>

                <el-form-item>
                    <el-button type="primary" @click="applyFilter">查詢</el-button>
                    <el-button @click="resetFilter">重置</el-button>
                </el-form-item>

                <!-- ⚙ 欄位設定 -->
                <el-popover trigger="click" placement="bottom-end" width="260">
                    <template #reference>
                        <el-button icon="el-icon-setting">欄位設定</el-button>
                    </template>
                    <el-checkbox-group v-model="visibleColumns" class="col-setting">
                        <el-checkbox v-for="col in allColumns" :key="col.prop" :label="col.prop">
                            {{ col.label }}
                        </el-checkbox>
                    </el-checkbox-group>
                </el-popover>
            </el-form>
        </div>

        <!-- 資料表 -->
        <el-table :data="pagedRows" border height="70vh">
            <el-table-column type="index" label="序號" width="80" />

            <el-table-column v-if="visibleColumns.includes('timestamp')" prop="timestamp" label="時間" width="180" />
            <el-table-column v-if="visibleColumns.includes('station_no')" prop="station_no" label="站點" width="100" />
            <el-table-column v-if="visibleColumns.includes('product_spec')" prop="product_spec" label="產品規格"
                width="120" />

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
                    <el-tag :type="row[col.prop] === 'NG' ? 'danger' : 'success'">{{ row[col.prop] }}</el-tag>
                </template>
            </el-table-column>

            <!-- 洩漏量欄位 -->
            <el-table-column v-for="col in visibleLeakColumns" :key="col.prop" :prop="col.prop" :label="col.label"
                width="180" />

            <!-- 維修建議與可能部位 -->
            <el-table-column label="維修建議" prop="suggestion" width="160" />
            <el-table-column label="可能部位" prop="part" width="140" />
        </el-table>

        <!-- 分頁 -->
        <div style="text-align:center; margin-top:12px;">
            <el-pagination background layout="prev, pager, next, sizes, total" :total="filteredRows.length"
                v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" />
        </div>
    </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'

// 分頁控制
const currentPage = ref(1)
const pageSize = ref(20)

// 篩選條件
const filters = ref({
    id: '',
    product_spec: '',
    range: [],
    status: '',
})

// 模擬資料
const rows = ref([
    {
        id: 1,
        timestamp: '2025-10-21 08:03:00',
        station_no: '2',
        product_spec: 'MAFR-302',
        ng_items: ['M04', 'M08'],
        M01: 'OK', M02: 'OK', M03: 'OK', M04: 'NG', M05: 'OK', M06: 'OK',
        M07: 'OK', M08: 'NG', M09: 'OK', M10: 'OK', M11: 'OK', M12: 'OK',
        M04_leak: '1.038', M05_leak: '6.499', M08_leak: '0.339', M11_leak: '5.422',
        suggestion: '更換帽型蓋 -> 吹淨S28 -> 吹淨帽型蓋 -> 吹淨活塞 -> 更換S28 -> 吹淨內杯',
        part: '帽型蓋'
    },
    {
        id: 2,
        timestamp: '2025-10-21 08:06:00',
        station_no: '4',
        product_spec: 'MAFR-302',
        ng_items: [],
        M01: 'OK', M02: 'OK', M03: 'OK', M04: 'OK', M05: 'OK', M06: 'OK',
        M07: 'OK', M08: 'OK', M09: 'OK', M10: 'OK', M11: 'OK', M12: 'OK',
        M04_leak: '0.626', M05_leak: '6.255', M08_leak: '0.323', M11_leak: '4.982',
        suggestion: '產品狀態良好，無需維修',
        part: '無'
    },
])

// 欄位設定
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

// 篩選邏輯
const filteredRows = computed(() => {
    return rows.value.filter(r => {
        const matchId = filters.value.id ? String(r.id) === String(filters.value.id) : true
        const matchSpec = filters.value.product_spec
            ? r.product_spec.toLowerCase().includes(filters.value.product_spec.toLowerCase())
            : true
        return matchId && matchSpec
    })
})

// 分頁處理
const pagedRows = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return filteredRows.value.slice(start, end)
})

function applyFilter() {
    currentPage.value = 1
}
function resetFilter() {
    filters.value = { id: '', product_spec: '', range: [], status: '' }
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
