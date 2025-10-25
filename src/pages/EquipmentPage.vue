<template>
    <el-card>
        <div class="toolbar">
            <el-input v-model="search" placeholder="搜尋設備名稱或代碼" style="max-width:260px" />
            <div>
                <el-button type="primary" @click="openForm()">新增設備</el-button>
                <el-button type="primary" @click="drawerVisible = true">型號對照表</el-button>
            </div>
        </div>

        <!-- 設備列表 + 展開站點 -->
        <el-table :data="filteredDevices" style="width: 100%" border>
            <el-table-column type="expand">
                <template #default="{ row }">
                    <el-table :data="row.stations" size="small" border>
                        <el-table-column prop="station_no" label="站點" width="100" />
                        <el-table-column prop="mode" label="模式" width="100" />
                        <el-table-column prop="enabled" label="啟用">
                            <template #default="{ row }">
                                <el-switch v-model="row.enabled" />
                            </template>
                        </el-table-column>
                        <el-table-column prop="last_test_at" label="最近測試" />
                    </el-table>
                </template>
            </el-table-column>

            <el-table-column prop="device_code" label="設備代號" width="140" />
            <el-table-column prop="name" label="名稱" />
            <el-table-column prop="location" label="位置" width="120" />
            <el-table-column prop="availability" label="稼動率" width="120" />
            <el-table-column prop="status" label="狀態" width="120">
                <template #default="{ row }">
                    <el-tag :type="statusColor(row.status)">{{ row.status }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="260">
                <template #default="{ row }">
                    <el-button size="small" type="primary" @click="openForm(row)">編輯</el-button>
                    <el-popconfirm title="確定刪除這台設備？" @confirm="removeDevice(row.id)">
                        <template #reference>
                            <el-button size="small" type="danger">刪除</el-button>
                        </template>
                    </el-popconfirm>
                </template>
            </el-table-column>
        </el-table>

        <!-- 型號對照表 Drawer -->
        <el-drawer v-model="drawerVisible" title="配方頻道 - 型號對照表" size="50%">
            <el-table :data="modelMap" border height="70vh">
                <el-table-column prop="channel" label="配方頻道" width="120" />
                <el-table-column label="型號">
                    <template #default="{ row }">
                        <!-- 頻道1固定顯示 -->
                        <template v-if="row.channel === 1">
                            <span>{{ row.model }}</span>
                        </template>

                        <!-- 其他頻道 -->
                        <template v-else>
                            <el-input v-if="row.editable" v-model="row.model" placeholder="輸入產品型號" />
                            <span v-else>{{ row.model }}</span>
                        </template>
                    </template>
                </el-table-column>
            </el-table>

            <div style="text-align:right; margin-top:10px;">
                <el-button @click="enableEdit">重新編輯</el-button>
                <el-button type="primary" @click="saveModelMap">儲存設定</el-button>
            </div>
        </el-drawer>

        <!-- 新增/編輯表單 -->
        <el-dialog v-model="dialogVisible" :title="editingDevice ? '編輯設備' : '新增設備'" width="500px">
            <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
                <el-form-item label="設備代號" prop="device_code">
                    <el-input v-model="form.device_code" />
                </el-form-item>
                <el-form-item label="名稱" prop="name">
                    <el-input v-model="form.name" />
                </el-form-item>
                <el-form-item label="位置" prop="location">
                    <el-input v-model="form.location" />
                </el-form-item>
                <el-form-item label="狀態" prop="status">
                    <el-select v-model="form.status" placeholder="選擇狀態">
                        <el-option label="online" value="online" />
                        <el-option label="offline" value="offline" />
                        <el-option label="maintenance" value="maintenance" />
                    </el-select>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="dialogVisible = false">取消</el-button>
                <el-button type="primary" @click="submitForm">儲存</el-button>
            </template>
        </el-dialog>
    </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const drawerVisible = ref(false)
const dialogVisible = ref(false)
const search = ref('')
const editingDevice = ref(null)
const formRef = ref(null)
const modelMap = ref([])

const devices = ref([
    {
        id: 1,
        device_code: 'ACD-001',
        name: '氣密檢測機 A1',
        location: '產線一區',
        availability: '98.5%',
        status: 'online',
        stations: [
            { id: 101, station_no: 1, enabled: true, mode: '自動', last_test_at: '2025-10-26 13:59' },
            { id: 102, station_no: 2, enabled: true, mode: '手動', last_test_at: '2025-10-26 13:50' },
            { id: 103, station_no: 3, enabled: false, mode: '停用', last_test_at: '-' },
            { id: 104, station_no: 4, enabled: true, mode: '自動', last_test_at: '2025-10-26 14:10' },
        ],
    },
    {
        id: 2,
        device_code: 'BCD-002',
        name: '氣密檢測機 B1',
        location: '產線二區',
        availability: '95.0%',
        status: 'offline',
        stations: [
            { id: 201, station_no: 1, enabled: true, mode: '手動', last_test_at: '2025-10-25 21:00' },
            { id: 202, station_no: 2, enabled: true, mode: '自動', last_test_at: '2025-10-26 08:10' },
            { id: 203, station_no: 3, enabled: false, mode: '停用', last_test_at: '-' },
            { id: 204, station_no: 4, enabled: true, mode: '自動', last_test_at: '2025-10-25 23:40' },
        ],
    },
    {
        id: 3,
        device_code: 'CCD-003',
        name: '氣密檢測機 C1',
        location: '產線三區',
        availability: '92.0%',
        status: 'maintenance',
        stations: [
            { id: 301, station_no: 1, enabled: true, mode: '維修', last_test_at: '-' },
            { id: 302, station_no: 2, enabled: false, mode: '停用', last_test_at: '-' },
            { id: 303, station_no: 3, enabled: false, mode: '停用', last_test_at: '-' },
            { id: 304, station_no: 4, enabled: false, mode: '停用', last_test_at: '-' },
        ],
    },
    {
        id: 4,
        device_code: 'DCD-004',
        name: '氣密檢測機 D1',
        location: '產線四區',
        availability: '98.5%',
        status: 'online',
        stations: [
            { id: 401, station_no: 1, enabled: true, mode: '自動', last_test_at: '2025-10-26 14:55' },
            { id: 402, station_no: 2, enabled: true, mode: '手動', last_test_at: '2025-10-26 14:40' },
            { id: 403, station_no: 3, enabled: true, mode: '自動', last_test_at: '2025-10-26 14:50' },
            { id: 404, station_no: 4, enabled: false, mode: '停用', last_test_at: '-' },
        ],
    },
])

const filteredDevices = computed(() => {
    if (!search.value) return devices.value
    const keyword = search.value.toLowerCase()
    return devices.value.filter(
        (d) =>
            d.name.toLowerCase().includes(keyword) ||
            d.device_code.toLowerCase().includes(keyword)
    )
})

function statusColor(status) {
    switch (status) {
        case 'online': return 'success'
        case 'offline': return 'danger'
        case 'maintenance': return 'warning'
        default: return 'info'
    }
}

const form = ref({
    device_code: '',
    name: '',
    location: '',
    status: 'online',
})

const rules = {
    device_code: [{ required: true, message: '必填', trigger: 'blur' }],
    name: [{ required: true, message: '必填', trigger: 'blur' }],
    location: [{ required: true, message: '必填', trigger: 'blur' }],
}

function openForm(device = null) {
    if (device) {
        // 編輯模式
        editingDevice.value = device
        form.value = { ...device }
    } else {
        // 新增模式
        editingDevice.value = null
        form.value = { device_code: '', name: '', location: '', status: 'online' }
    }
    dialogVisible.value = true
}

function submitForm() {
    formRef.value.validate((valid) => {
        if (!valid) return
        if (editingDevice.value) {
            // 編輯
            const index = devices.value.findIndex((d) => d.id === editingDevice.value.id)
            if (index !== -1) devices.value[index] = { ...editingDevice.value, ...form.value }
        } else {
            // 新增
            const newDevice = {
                ...form.value,
                id: devices.value.length + 1,
                stations: [
                    { id: `${devices.value.length}01`, station_no: 1, enabled: true, mode: '自動', last_test_at: '-' },
                    { id: `${devices.value.length}02`, station_no: 2, enabled: true, mode: '自動', last_test_at: '-' },
                    { id: `${devices.value.length}03`, enabled: false, mode: '停用', last_test_at: '-' },
                    { id: `${devices.value.length}04`, enabled: false, mode: '停用', last_test_at: '-' },
                ],
            }
            devices.value.push(newDevice)
        }
        dialogVisible.value = false
    })
}

function removeDevice(id) {
    devices.value = devices.value.filter((d) => d.id !== id)
}

for (let i = 1; i <= 100; i++) {
    modelMap.value.push({
        channel: i,
        model: i === 1 ? 'MAFR-302' : '',
        editable: i !== 1,
    })
}

function saveModelMap() {
    modelMap.value.forEach((item) => {
        if (item.model && item.editable) {
            item.editable = false
        }
    })
    ElMessage.success('型號設定已更新')
    console.table(modelMap.value)
}

function enableEdit() {
    modelMap.value.forEach((item) => {
        if (item.channel !== 1) {
            item.editable = true
        }
    })
    ElMessage.info('已開啟重新編輯模式')
}
</script>

<style scoped>
.toolbar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
}
</style>
