<template>
    <!-- 查詢條件區 -->
    <el-card>
        <el-form :inline="true" :model="form" label-width="100px" class="qform">
            <el-form-item label="產品規格">
                <el-input v-model="form.product_spec" placeholder="e.g. MAFR-302" />
            </el-form-item>

            <el-form-item label="生產時段">
                <el-date-picker v-model="form.range" type="datetimerange" range-separator="至" start-placeholder="開始"
                    end-placeholder="結束" value-format="YYYY-MM-DD HH:mm:ss" />
            </el-form-item>

            <el-form-item label="狀態">
                <el-select v-model="form.status" placeholder="全部" style="width: 120px">
                    <el-option label="全部" value="" />
                    <el-option label="OK" value="OK" />
                    <el-option label="NG" value="NG" />
                </el-select>
            </el-form-item>

            <el-form-item>
                <el-button type="primary" @click="onSearch">查詢</el-button>
                <el-button @click="reset">重置</el-button>
            </el-form-item>
        </el-form>
    </el-card>

    <!-- 測試紀錄表 -->
    <el-card style="margin-top:12px">
        <el-table :data="filteredRows" height="520" border>
            <el-table-column prop="timestamp" label="時間" width="180" sortable />
            <el-table-column prop="station_no" label="站點" width="100" />
            <el-table-column prop="product_spec" label="產品規格" width="120" />
            <el-table-column prop="M04" label="一次測 (M04)" width="150" />
            <el-table-column prop="M05" label="一次測 (M05)" width="150" />
            <el-table-column prop="M08" label="二次測 (M08)" width="150" />
            <el-table-column prop="M11" label="二次測 (M11)" width="150" />
            <el-table-column label="狀態" width="100">
                <template #default="{ row }">
                    <el-tag :type="row.status === 'OK' ? 'success' : 'danger'">{{ row.status }}</el-tag>
                </template>
            </el-table-column>

            <!-- 新增操作欄：開啟分析 -->
            <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                    <el-button type="primary" size="small" @click="openAnalysis(row)">
                        分析
                    </el-button>
                </template>
            </el-table-column>
        </el-table>
    </el-card>

    <!-- Drawer：品質分析 -->
    <el-drawer v-model="drawerVisible" title="品質分析報告" size="45%">
        <AnalysisPanel v-if="selectedRecord" :record="selectedRecord" />
    </el-drawer>
</template>

<script setup>
import { ref } from "vue";
import AnalysisPanel from "@/components/AnalysisPanel.vue";

// -------------------------------
// 查詢條件
// -------------------------------
const form = ref({
    product_spec: "",
    range: [],
    status: "",
});

// -------------------------------
// 假資料
// -------------------------------
const rows = ref([
    { timestamp: "2025-10-21 08:03:00", station_no: "2", product_spec: "MAFR-302", M04: "1.038", M05: "6.499", M08: "0.339", M11: "5.422", status: "OK" },
    { timestamp: "2025-10-21 08:06:00", station_no: "4", product_spec: "MAFR-302", M04: "0.626", M05: "6.255", M08: "0.323", M11: "4.982", status: "OK" },
    { timestamp: "2025-10-21 08:15:00", station_no: "3", product_spec: "MAFR-302", M04: "0.404", M05: "12.197", M08: "0.000", M11: "0.000", status: "NG" },
    { timestamp: "2025-10-21 08:21:00", station_no: "2", product_spec: "MAFR-303", M04: "0.749", M05: "6.271", M08: "0.927", M11: "5.381", status: "OK" },
    { timestamp: "2025-10-21 08:45:00", station_no: "3", product_spec: "MAFR-304", M04: "0.459", M05: "6.344", M08: "0.145", M11: "5.230", status: "OK" },
]);

const filteredRows = ref([...rows.value]);

// -------------------------------
// 查詢邏輯
// -------------------------------
function onSearch() {
    const spec = form.value.product_spec.trim().toLowerCase();
    const [start, end] = form.value.range;
    const status = form.value.status;

    filteredRows.value = rows.value.filter((r) => {
        const matchSpec = spec ? r.product_spec.toLowerCase().includes(spec) : true;
        const matchTime =
            start && end
                ? new Date(r.timestamp) >= new Date(start) &&
                new Date(r.timestamp) <= new Date(end)
                : true;
        const matchStatus = status ? r.status === status : true;
        return matchSpec && matchTime && matchStatus;
    });
}

function reset() {
    form.value = { product_spec: "", range: [], status: "" };
    filteredRows.value = rows.value;
}

// -------------------------------
// Drawer 控制
// -------------------------------
const drawerVisible = ref(false);
const selectedRecord = ref(null);

function openAnalysis(row) {
    selectedRecord.value = row;
    drawerVisible.value = true;
}
</script>

<style scoped>
.qform {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: flex-end;
}
</style>
