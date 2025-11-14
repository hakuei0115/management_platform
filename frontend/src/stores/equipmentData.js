import { defineStore } from 'pinia'
import { ref } from 'vue'
import { EquipmentDataAPI } from '@/services/equipmentData'

export const useEquipmentDataStore = defineStore('equipmentData', () => {
    const equipmentDataList = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function fetchEquipmentData(filterParams) {
        loading.value = true
        error.value = null

        try {
            const res = await EquipmentDataAPI.fetchEquipmentData(filterParams);

            equipmentDataList.value = res;
        } catch (err) {
            console.error('fetchEquipmentData error:', err)
            error.value = err.message || '無法取得設備數據'
            throw error.value // 再拋回前端組件
        } finally {
            loading.value = false
        }
    }

    return {
        equipmentDataList,
        loading,
        error,
        fetchEquipmentData
    }
})