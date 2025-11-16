<template>
    <el-card class="equipment-page">
        <div class="toolbar">
            <el-input v-model="search" placeholder="搜尋設備名稱或代碼" style="max-width:260px" clearable />
            <div>
                <el-button type="primary" @click="openForm()">新增設備</el-button>
            </div>
        </div>

        <!-- 表格區 -->
        <el-table v-loading="loading" :data="filteredDevices" border row-key="id" style="width: 100%"
            @expand-change="getStations">
            <el-table-column type="expand">
                <template #default="{ row }">
                    <div class="station-header">
                        <h4>{{ row.name }} - 站點清單</h4>
                        <el-button size="small" type="success" @click="addStation(row)">新增站點</el-button>
                    </div>
                    <el-table :data="stationStore.stationMap[row.id]" size="small" border>
                        <el-table-column prop="id" label="站點" width="100" />
                        <el-table-column prop="enabled" label="啟用" width="100">
                            <template #default="{ row: station }">
                                <el-switch v-model="station.enabled" :active-value="1" :inactive-value="0"
                                    @click="updateStation(row, station)" />
                            </template>
                        </el-table-column>
                        <el-table-column label="操作" width="100">
                            <template #default="{ row: station }">
                                <el-button size="small" type="danger"
                                    @click="deleteStation(row, station)">刪除</el-button>
                            </template>
                        </el-table-column>
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
            <el-table :data="modelMappingsStore.modelMappings[activeDevice?.id] || []" border height="70vh">
                <el-table-column prop="channel" label="配方頻道" width="120" />

                <el-table-column label="型號">
                    <template #default="{ row }">
                        <el-input v-if="row.editable" v-model="row.model_name" placeholder="輸入產品型號" size="small" />
                        <span v-else>{{ row.model_name }}</span>
                    </template>
                </el-table-column>

                <el-table-column label="操作" width="200">
                    <template #default="{ row }">
                        <el-button v-if="!row.editable" size="small" type="primary" @click="row.editable = true">
                            編輯
                        </el-button>

                        <el-button v-else size="small" type="success" @click="saveSingleMapping(activeDevice.id, row)">
                            儲存
                        </el-button>

                        <el-popconfirm title="確定刪除此型號？" @confirm="deleteMapping(activeDevice.id, row)">
                            <template #reference>
                                <el-button size="small" type="danger">刪除</el-button>
                            </template>
                        </el-popconfirm>
                    </template>
                </el-table-column>
            </el-table>

            <div style="text-align:right; margin-top:10px;">
                <el-button size="small" type="primary" @click="openAddDialog">
                    新增型號
                </el-button>
            </div>
        </el-drawer>

        <!-- 新增型號 Dialog -->
        <el-dialog v-model="addDialogVisible" title="新增型號對照" width="400px" @keydown.enter="submitAddMapping">
            <el-form :model="addForm" label-width="100px">
                <el-form-item label="配方頻道" prop="channel" type="number" required>
                    <el-input v-model="addForm.channel" placeholder="請輸入配方頻道" />
                </el-form-item>

                <el-form-item label="型號名稱" prop="model_name" type="text" required>
                    <el-input v-model="addForm.model_name" placeholder="請輸入型號名稱" />
                </el-form-item>
            </el-form>

            <template #footer>
                <el-button @click="addDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="submitAddMapping">儲存</el-button>
            </template>
        </el-dialog>



        <!-- 新增/編輯表單 -->
        <el-dialog v-model="dialogVisible" :title="editingDevice ? '編輯設備' : '新增設備'" width="500px" @keydown.enter="submitForm">
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { useEquipmentStore } from '@/stores/equipment'
import { useStationStore } from '@/stores/stations'
import { useModelMappingsStore } from '@/stores/modelMappings'

const equipmentStore = useEquipmentStore()
const stationStore = useStationStore()
const modelMappingsStore = useModelMappingsStore()
const search = ref('')
const drawerVisible = ref(false)
const dialogVisible = ref(false)
const editingDevice = ref(null)
const formRef = ref(null)
const activeDevice = ref(null)
const activeModelMap = ref([])
const loading = ref(false)
const addDialogVisible = ref(false);
const addForm = ref({ channel: '', model_name: '' });

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
    if (stationStore.stationMap[row.id]) {
        loading.value = false

        return stationStore.stationMap[row.id]
    }

    try {
        await stationStore.fetchStationList(row.id)

        return stationStore.stationMap[row.id]
    } catch (error) {
        ElMessage.error(error.message || '取得站點資料失敗')
        return []
    } finally {
        loading.value = false
    }
}

async function addStation(row) {
    loading.value = true;
    const equipment_id = row.id;

    try {
        const list = stationStore.stationMap[equipment_id] || [];

        // 取出現有的 station_no 並轉成數字
        const existingNos = list.map(s => Number(s.station_no));

        // 找出最小可用站號
        let nextStationNo = 1;
        while (existingNos.includes(nextStationNo)) {
            nextStationNo++;
        }

        // 生成唯一 id（你原本的格式）
        const newStation = {
            id: `${equipment_id}0${nextStationNo}`,
            equipment_id,
            station_no: nextStationNo,
            enabled: 1,
        };

        await stationStore.insertStation(equipment_id, newStation);
        ElMessage.success(`新增站點成功（編號 ${nextStationNo}）`);

        await getStations(row);
    } catch (error) {
        ElMessage.error(error.message || '新增站點失敗');
    } finally {
        loading.value = false;
    }
}

async function updateStation(row, station) {
    loading.value = true
    const equipment_id = row.id;

    try {
        await stationStore.updateStation(
            equipment_id,
            station.id,
            {
                id: station.id,
                equipment_id: equipment_id,
                station_no: station.station_no,
                enabled: station.enabled,
            }
        );
        ElMessage.success('站點已更新');
        await getStations(row);
    } catch (error) {
        ElMessage.error(error.message || '更新站點失敗')
    } finally {
        loading.value = false
    }
}

async function deleteStation(row, station) {
    loading.value = true
    const equipment_id = row.id;
    try {
        await stationStore.deleteStation(equipment_id, station.id);
        ElMessage.success('站點已刪除');
        await getStations(row);
    } catch (error) {
        ElMessage.error(error.message || '刪除站點失敗')
    } finally {
        loading.value = false
    }
}

async function getModelMapping(row) {
    loading.value = true
    try {
        await modelMappingsStore.fetchModelMappings(row.id);
    } catch (error) {
        ElMessage.error(error.message || '取得型號對照表失敗')
    } finally {
        loading.value = false
    }
}

// 模型邏輯
async function openModelDrawer(device) {
    activeDevice.value = device
    await getModelMapping(device)
    activeModelMap.value = modelMappingsStore.modelMappings || []
    drawerVisible.value = true
}

function openAddDialog() {
    addForm.value = { channel: '', model_name: '' };
    addDialogVisible.value = true;
}

async function saveSingleMapping(equipmentId, mapping) {
    try {
        loading.value = true;
        await modelMappingsStore.updateModelMapping(equipmentId, mapping.id, {
            channel: mapping.channel,
            model_name: mapping.model_name,
        });
        mapping.editable = false;
        ElMessage.success(`配方頻道 ${mapping.channel} 已更新`);
    } catch (error) {
        console.error('saveSingleMapping error:', error);
        ElMessage.error(error.message || '更新型號失敗');
    } finally {
        loading.value = false;
    }
}

async function deleteMapping(equipmentId, mapping) {
    try {
        loading.value = true;
        await modelMappingsStore.deleteModelMapping(equipmentId, mapping.id);
        await modelMappingsStore.fetchModelMappings(equipmentId);
        ElMessage.success('型號已刪除');
    } catch (error) {
        console.error('deleteMapping error:', error);
        ElMessage.error(error.message || '刪除型號失敗');
    } finally {
        loading.value = false;
    }
}

async function submitAddMapping() {
    const equipmentId = activeDevice.value.id
    const existing = modelMappingsStore.modelMappings[equipmentId] || []

    if (!addForm.value.channel || !addForm.value.model_name) {
        ElMessage.error('請填寫完整的型號資訊')
        return
    }

    if (addForm.value.channel <= 0 || !Number.isInteger(Number(addForm.value.channel))) {
        ElMessage.error('配方頻道必須為正整數')
        return
    }

    const duplicate = existing.find(
        m => String(m.channel) === String(addForm.value.channel)
    )

    if (duplicate) {
        try {
            await ElMessageBox.confirm(
                `配方頻道 ${addForm.value.channel} 已存在（目前型號：${duplicate.model_name}），是否覆蓋？`,
                '頻道重複警告',
                { type: 'warning' }
            )

            await modelMappingsStore.updateModelMapping(equipmentId, duplicate.id, addForm.value)
            await modelMappingsStore.fetchModelMappings(equipmentId)
            ElMessage.success('已覆蓋原有型號設定')
            addDialogVisible.value = false
            return
        } catch {
            return
        }
    }

    try {
        loading.value = true
        await modelMappingsStore.insertModelMapping(equipmentId, addForm.value)
        await modelMappingsStore.fetchModelMappings(equipmentId)
        ElMessage.success('新增型號成功')
        addDialogVisible.value = false
    } catch (error) {
        ElMessage.error(error.message || '新增型號失敗')
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
