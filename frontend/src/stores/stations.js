import { defineStore } from 'pinia'
import { ref } from 'vue'
import { StationAPI } from '@/services/stations'

export const useStationStore = defineStore('station', () => {
    const stationMap = ref({});
    const loading = ref(false);
    const error = ref(null);

    async function fetchStationList(equipmentId) {
        loading.value = true;
        error.value = null;

        try {
            const res = await StationAPI.fetchStationList(equipmentId);

            if (res.length !== 0) {
                stationMap.value[equipmentId] = res.stations;
            } else {
                stationMap.value[equipmentId] = [];
                throw new Error(res.message || '取得站點列表失敗');
            }
        } catch (err) {
            console.error('fetchStationList error:', err);
            error.value = err.message || '無法取得站點列表';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function insertStation(equipmentId, stationData) {
        loading.value = true;
        error.value = null;

        try {
            const payload = stationData?.value ? stationData.value : stationData;
            const res = await StationAPI.insertStation(equipmentId, payload);

            if (res.success) {
                if (!stationMap.value[equipmentId]) stationMap.value[equipmentId] = [];
                stationMap.value[equipmentId].push(payload);
            } else {
                throw new Error(res.message || '新增站點失敗');
            }

            return res;
        } catch (err) {
            console.error('insertStation error:', err);
            error.value = err.message || '新增站點時發生錯誤';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function updateStation(equipmentId, stationId, stationData) {
        loading.value = true;
        error.value = null;

        try {
            const payload = stationData?.value ? stationData.value : stationData;
            const res = await StationAPI.updateStation(equipmentId, stationId, payload);

            if (res.success) {
                const list = stationMap.value[equipmentId]
                if (list) {
                    const index = list.findIndex(station => station.id === stationId)
                    if (index !== -1) list[index] = { ...list[index], ...payload }
                }
            } else {
                throw new Error(res.message || '更新站點失敗');
            }

            return res;
        } catch (err) {
            console.error('updateStation error:', err);
            error.value = err.message || '更新站點時發生錯誤';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function deleteStation(equipmentId, stationId) {
        loading.value = true;
        error.value = null;

        try {
            const res = await StationAPI.deleteStation(equipmentId, stationId);

            if (res.success) {
                const list = stationMap.value[equipmentId];
                if (list) {
                    stationMap.value[equipmentId] = list.filter(station => station.id !== stationId);
                }
            } else {
                throw new Error(res.message || '刪除站點失敗');
            }

            return res;
        } catch (err) {
            console.error('deleteStation error:', err);
            error.value = err.message || '刪除站點時發生錯誤';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    return {
        stationMap,
        loading,
        error,
        fetchStationList,
        insertStation,
        updateStation,
        deleteStation,
    };
});