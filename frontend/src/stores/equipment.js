import { defineStore } from 'pinia'
import { ref } from 'vue'
import { EquipmentAPI } from '@/services/equipment'

export const useEquipmentStore = defineStore('equipment', () => {
    const equipmentList = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function fetchEquipmentList() {
        loading.value = true
        error.value = null

        try {
            const res = await EquipmentAPI.fetchEquipmentList()
            if (res.length !== 0) {
                equipmentList.value = res.equipment || []
            } else {
                throw new Error(res.message || '取得設備列表失敗')
            }
        } catch (err) {
            console.error('fetchEquipmentList error:', err)
            error.value = err.message || '無法取得設備列表'
            throw error.value // 再拋回前端組件
        } finally {
            loading.value = false
        }
    }

    async function insertEquipment(equipmentData) {
        loading.value = true
        error.value = null

        try {
            const payload = equipmentData?.value ? equipmentData.value : equipmentData
            const res = await EquipmentAPI.insertEquipment(payload)

            if (res.success) {
                equipmentList.value.push(payload) // 成功時更新狀態
            } else {
                throw new Error(res.message || '新增設備失敗')
            }

            return res
        } catch (err) {
            console.error('insertEquipment error:', err)
            error.value = err.message || '新增設備時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    async function updateEquipment(id, equipmentData) {
        loading.value = true
        error.value = null

        try {
            const payload = equipmentData?.value ? equipmentData.value : equipmentData
            const res = await EquipmentAPI.updateEquipment(id, payload)

            if (res.success) {
                const index = equipmentList.value.findIndex(d => d.id === id)
                if (index !== -1) equipmentList.value[index] = { ...equipmentList.value[index], ...payload }
            } else {
                throw new Error(res.message || '更新設備失敗')
            }

            return res
        } catch (err) {
            console.error('updateEquipment error:', err)
            error.value = err.message || '更新設備時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    async function deleteEquipment(id) {
        loading.value = true
        error.value = null

        try {
            const res = await EquipmentAPI.deleteEquipment(id)
            if (res.success) {
                equipmentList.value = equipmentList.value.filter(d => d.id !== id)
            } else {
                throw new Error(res.message || '刪除設備失敗')
            }
            return res
        } catch (err) {
            console.error('deleteEquipment error:', err)
            error.value = err.message || '刪除設備時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    return {
        equipmentList,
        loading,
        error,
        fetchEquipmentList,
        insertEquipment,
        updateEquipment,
        deleteEquipment
    }
})
