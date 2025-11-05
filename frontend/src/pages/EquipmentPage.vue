<template>
    <el-card class="equipment-page">
        <div class="toolbar">
            <el-input v-model="search" placeholder="搜尋設備名稱或代碼" style="max-width:260px" />
            <el-button type="primary" @click="openForm()">新增設備</el-button>
        </div>

        <!-- 設備列表 + 展開站點 -->
        <el-table :data="filteredDevices" style="width: 100%" border row-key="id"
            v-model:expand-row-keys="expandedRows">
            <el-table-column type="expand">
                <template #default="{ row }">
                    <div class="station-header">
                        <h4>{{ row.name }} - 站點清單</h4>
                        <el-button size="small" type="success" @click="addStation(row)">新增站點</el-button>
                    </div>
                    <el-table :data="row.stations" size="small" border>
                        <el-table-column prop="station_no" label="站點" width="100" />
                        <el-table-column prop="enabled" label="啟用" width="100">
                            <template #default="{ row: station }">
                                <el-switch v-model="station.enabled" @change="onStationToggle(row.id, station)" />
                            </template>
                        </el-table-column>
                        <el-table-column prop="last_test_at" label="最近測試" />
                    </el-table>
                </template>
            </el-table-column>

            <el-table-column prop="device_code" label="設備代號" width="140" />
            <el-table-column prop="name" label="名稱" />
            <el-table-column prop="location" label="位置" width="120" />
            <el-table-column prop="status" label="狀態" width="120">
                <template #default="{ row }">
                    <el-tag :type="statusColor(row.status)">{{ row.status }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="300">
                <template #default="{ row }">
                    <el-button size="small" type="primary" @click="openForm(row)">編輯</el-button>
                    <el-button size="small" type="info" @click="openModelDrawer(row)">型號對照表</el-button>
                    <el-popconfirm title="確定刪除這台設備？" @confirm="removeDevice(row.id)">
                        <template #reference>
                            <el-button size="small" type="danger">刪除</el-button>
                        </template>
                    </el-popconfirm>
                </template>
            </el-table-column>
        </el-table>

        <!-- 型號對照表 Drawer -->
        <el-drawer v-model="drawerVisible" :title="activeDevice ? `型號對照表 - ${activeDevice.name}` : '型號對照表'" size="45%">
            <el-table :data="activeModelMap" border height="70vh">
                <el-table-column prop="channel" label="配方頻道" width="120" />
                <el-table-column label="型號">
                    <template #default="{ row }">
                        <el-input v-if="row.editable" v-model="row.model" placeholder="輸入產品型號" />
                        <span v-else>{{ row.model }}</span>
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
const expandedRows = ref([])

const activeDevice = ref(null)
const activeModelMap = ref([])

const devices = ref([
    {
        id: 1,
        device_code: 'ACD-001',
        name: '氣密檢測機 A1',
        location: '產線一區',
        status: 'online',
        stations: [
            { id: 101, station_no: 1, enabled: true, last_test_at: '2025-10-26 13:59' },
            { id: 102, station_no: 2, enabled: true, last_test_at: '2025-10-26 13:50' },
            { id: 103, station_no: 3, enabled: false, last_test_at: '-' },
            { id: 104, station_no: 4, enabled: false, last_test_at: '-' },
        ],
        modelMap: Array.from({ length: 100 }, (_, i) => ({
            channel: i + 1,
            model: i === 0 ? 'MAFR-302' : '',
            editable: i !== 0,
        })),
    },
    {
        id: 2,
        device_code: 'BCD-002',
        name: '氣密檢測機 B1',
        location: '產線二區',
        status: 'offline',
        stations: [
            { id: 201, station_no: 1, enabled: true, last_test_at: '2025-10-25 21:00' },
            { id: 202, station_no: 2, enabled: false, last_test_at: '-' },
            { id: 203, station_no: 3, enabled: false, last_test_at: '-' },
            { id: 204, station_no: 4, enabled: false, last_test_at: '-' },
        ],
        modelMap: Array.from({ length: 100 }, (_, i) => ({
            channel: i + 1,
            model: '',
            editable: true,
        })),
    },
    {
        id: 3,
        device_code: 'CCD-003',
        name: '氣密檢測機 C1',
        location: '產線三區',
        status: 'maintenance',
        stations: [
            { id: 301, station_no: 1, enabled: true, last_test_at: '-' },
            { id: 302, station_no: 2, enabled: false, last_test_at: '-' },
            { id: 303, station_no: 3, enabled: false, last_test_at: '-' },
            { id: 304, station_no: 4, enabled: false, last_test_at: '-' },
        ],
        modelMap: Array.from({ length: 100 }, (_, i) => ({
            channel: i + 1,
            model: '',
            editable: true,
        })),
    },
    {
        id: 4,
        device_code: 'DCD-004',
        name: '氣密檢測機 D1',
        location: '產線四區',
        status: 'online',
        stations: [
            { id: 401, station_no: 1, enabled: true, last_test_at: '2025-10-26 14:55' },
            { id: 402, station_no: 2, enabled: true, last_test_at: '2025-10-26 14:40' },
            { id: 403, station_no: 3, enabled: true, last_test_at: '2025-10-26 14:50' },
            { id: 404, station_no: 4, enabled: false, last_test_at: '-' },
        ],
        modelMap: Array.from({ length: 100 }, (_, i) => ({
            channel: i + 1,
            model: '',
            editable: true,
        })),
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

function onStationToggle(deviceId, station) {
    console.log(`設備 ${deviceId} 的站點 ${station.station_no} 改為`, station.enabled)
}

function addStation(device) {
    const nextNo = device.stations.length + 1
    device.stations.push({
        id: Date.now(),
        station_no: nextNo,
        enabled: true,
        last_test_at: '-',
    })
    ElMessage.success(`已新增站點 ${nextNo}`)
}

// === 型號對照表 ===
function openModelDrawer(device) {
    activeDevice.value = device
    activeModelMap.value = device.modelMap
    drawerVisible.value = true
}

function enableEdit() {
    activeModelMap.value.forEach((item) => (item.editable = true))
    ElMessage.info('已開啟重新編輯模式')
}

function saveModelMap() {
    activeModelMap.value.forEach((item) => (item.editable = false))
    ElMessage.success('型號設定已更新')
}

// === 新增/編輯設備 ===
const form = ref({ device_code: '', name: '', location: '', status: 'online' })
const rules = {
    device_code: [{ required: true, message: '必填', trigger: 'blur' }],
    name: [{ required: true, message: '必填', trigger: 'blur' }],
    location: [{ required: true, message: '必填', trigger: 'blur' }],
}

function openForm(device = null) {
    if (device) {
        editingDevice.value = device
        form.value = { ...device }
    } else {
        editingDevice.value = null
        form.value = { device_code: '', name: '', location: '', status: 'online' }
    }
    dialogVisible.value = true
}

function submitForm() {
    formRef.value.validate((valid) => {
        if (!valid) return
        if (editingDevice.value) {
            const index = devices.value.findIndex((d) => d.id === editingDevice.value.id)
            if (index !== -1) devices.value[index] = { ...editingDevice.value, ...form.value }
        } else {
            const newDevice = {
                ...form.value,
                id: Date.now(),
                stations: [],
                modelMap: Array.from({ length: 10 }, (_, i) => ({
                    channel: i + 1,
                    model: '',
                    editable: true,
                })),
            }
            devices.value.push(newDevice)
        }
        dialogVisible.value = false
    })
}

function removeDevice(id) {
    devices.value = devices.value.filter((d) => d.id !== id)
}
</script>

<style scoped>
.toolbar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
}

.station-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}

.el-table th,
.el-table td {
    font-size: 15px;
}

.el-input,
.el-button {
    font-size: 15px;
}
</style>
