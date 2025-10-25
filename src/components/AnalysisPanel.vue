<template>
    <div v-if="record">
        <h3>產品資訊</h3>
        <el-descriptions :column="2" border>
            <el-descriptions-item label="產品規格">{{ record.product_spec }}</el-descriptions-item>
            <el-descriptions-item label="測試時間">{{ record.timestamp }}</el-descriptions-item>
            <el-descriptions-item label="站點">{{ record.station_no }}</el-descriptions-item>
            <el-descriptions-item label="狀態">
                <el-tag :type="record.status === 'OK' ? 'success' : 'danger'">{{ record.status }}</el-tag>
            </el-descriptions-item>
        </el-descriptions>

        <h3 style="margin-top: 16px;">測試項結果</h3>
        <el-table :data="[record]" border>
            <el-table-column prop="M04" label="一次測 (M04)" />
            <el-table-column prop="M05" label="一次測 (M05)" />
            <el-table-column prop="M08" label="二次測 (M08)" />
            <el-table-column prop="M11" label="二次測 (M11)" />
        </el-table>

        <h3 style="margin-top: 16px;">模型預測結果</h3>
        <el-card>
            <p><b>維修建議：</b> {{ suggestion.suggestion }}</p>
            <p><b>可能部位：</b> {{ suggestion.part }}</p>
        </el-card>
    </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
    record: Object,
});

// 模型預測假邏輯
const suggestion = computed(() => {
    const r = props.record;
    if (!r) return { suggestion: "-", part: "-" };

    // 假邏輯：M05 或 M11 超標視為洩漏
    const status = r.status;
    if (status === "NG") {
        return {
            suggestion: "吹淨帽型蓋",
            part: "帽型蓋",
        };
    } else {
        return {
            suggestion: "產品狀態良好，無需維修",
            part: "無",
        };
    }
});
</script>
