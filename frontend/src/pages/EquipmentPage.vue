<template>
    <el-card class="equipment-page">
        <div class="toolbar">
            <el-input v-model="search" placeholder="搜尋設備名稱或代碼" style="max-width:260px" clearable />
            <div>
                <el-button type="primary" @click="openForm()">新增設備</el-button>
                <el-button @click="fetchList">重新整理</el-button>
            </div>
        </div>

        <!-- 表格區 -->
        <el-table v-loading="loading" :data="filteredDevices" border row-key="id" style="width: 100%"
            v-model:expand-row-keys="expandedRows" @expand-change="getStations">
            <el-table-column type="expand">
                <template #default="{ row }">
                    <div class="station-header">
                    <h4>{{ row.name }} - 站點清單</h4>
                    <el-button size="small" type="success" @click="addStation(row)">新增站點</el-button>
                    </div>
                    <el-table :data="stationStore.stationList" size="small" border>
                    <el-table-column prop="station_no" label="站點" width="100" />
                    <el-table-column prop="enabled" label="啟用" width="100">
                        <template #default="{ row: station }">
                            <el-switch v-model="station.enabled" :active-value="1" :inactive-value="0" />
                        </template>
                    </el-table-column>
                    <el-table-column prop="last_test_at" label="最近測試" />
                    </el-table>
                </template>
            </el-table-column>

            <el-table-column prop="equipment_code" label="設備代號" width="140" />
            <el-table-column prop="name" label="名稱" />
            <el-table-column prop="install_location" label="位置" width="120" />
            <el-table-column prop="status" label="狀態" width="120">
                <template #default="{ row }">
                    <el-tag :type="statusColor(row.status)">{{ row.status }}</el-tag>
                </template>
            </el-table-column>

            <el-table-column label="操作" width="260">
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
                <el-form-item label="設備代號" prop="equipment_code">
                    <el-input v-model="form.equipment_code" />
                </el-form-item>
                <el-form-item label="名稱" prop="name">
                    <el-input v-model="form.name" />
                </el-form-item>
                <el-form-item label="位置" prop="install_location">
                    <el-input v-model="form.install_location" />
                </el-form-item>
                <el-form-item label="狀態" prop="status">
                    <el-select v-model="form.status">
                        <el-option label="running" value="running" />
                        <el-option label="offline" value="offline" />
                        <el-option label="standby" value="standby" />
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useEquipmentStore } from '@/stores/equipment'
import { useStationStore } from '@/stores/stations'

const equipmentStore = useEquipmentStore()
const stationStore = useStationStore()
const search = ref('')
const drawerVisible = ref(false)
const dialogVisible = ref(false)
const editingDevice = ref(null)
const formRef = ref(null)
const expandedRows = ref([])
const activeDevice = ref(null)
const activeModelMap = ref([])
const loading = ref(false)

async function fetchList() {
    loading.value = true
    try {
        await equipmentStore.fetchEquipmentList();
    } catch (err) {
        ElMessage.error(err.message || '取得設備列表失敗')
    } finally {
        loading.value = false
    }
}
onMounted(fetchList)

async function getStations(row) {
    loading.value = true
    try {
        await stationStore.fetchStationList(row.id)

        console.log(stationStore.stationList);

        return stationStore.stationList
    } catch (error) {
        ElMessage.error(error.message || '取得站點資料失敗')
        return []
    } finally {
        loading.value = false
    }
}

const filteredDevices = computed(() => {
    const list = equipmentStore.equipmentList || []
    if (!search.value) return list
    const keyword = search.value.toLowerCase()
    return list.filter(
        d =>
            d.name.toLowerCase().includes(keyword) ||
            d.equipment_code.toLowerCase().includes(keyword)
    )
})

function statusColor(status) {
    switch (status) {
        case 'running': return 'success'
        case 'offline': return 'danger'
        case 'standby': return 'warning'
        default: return 'info'
    }
}

// 模型邏輯
function openModelDrawer(device) {
    activeDevice.value = device
    activeModelMap.value = device.modelMap || []
    drawerVisible.value = true
}
function enableEdit() {
    activeModelMap.value.forEach(i => i.editable = true)
}
function saveModelMap() {
    activeModelMap.value.forEach(i => i.editable = false)
    ElMessage.success('型號設定已更新')
}

// 表單邏輯
const form = ref({ equipment_code: '', name: '', install_location: '', status: 'running' })
const rules = {
    equipment_code: [{ required: true, message: '必填', trigger: 'blur' }],
    name: [{ required: true, message: '必填', trigger: 'blur' }],
    install_location: [{ required: true, message: '必填', trigger: 'blur' }],
}
function openForm(device = null) {
    editingDevice.value = device
    form.value = device ? { ...device } : { equipment_code: '', name: '', install_location: '', status: 'running' }
    dialogVisible.value = true
}
async function submitForm() {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    ElMessage.success(editingDevice.value ? '設備更新成功' : '新增成功')

    if (!editingDevice.value) {
        await equipmentStore.insertEquipment(form.value);
        fetchList();
    } else {
        await equipmentStore.updateEquipment(editingDevice.value.id, form.value);
        fetchList();
    }

    dialogVisible.value = false
}

async function removeDevice(id) {
    try {
        await equipmentStore.deleteEquipment(id);
        ElMessage.success('設備已刪除');
        fetchList();
    } catch (err) {
        ElMessage.error(err.message || '刪除設備失敗')
    }
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
</style>
