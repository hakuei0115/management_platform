import api from './axiosInstance';

export const StationAPI = {
    async fetchStationList(equipmentId) {
        try {
            const res = await api.get(`/equipments/${equipmentId}/stations`);

            console.log(res);

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '取得站點列表失敗，請稍後再試');
            }
        } catch (error) {
            console.error('StationAPI.fetchStationList error:', error);
            throw error.response?.data || { message: '取得站點列表失敗，請稍後再試' };
        }
    },

    async insertStation(equipmentId, stationData) {
        try {
            const res = await api.post(`/equipments/${equipmentId}/stations`, stationData);

            return res.data;
        } catch (error) {
            console.error('StationAPI.insertStation error:', error);
            throw error.response?.data || { message: '新增站點失敗，請稍後再試' };
        }
    },

    async updateStation(equipmentId, stationId, stationData) {
        try {
            const res = await api.put(`/equipments/${equipmentId}/stations/${stationId}`, stationData);

            return res.data;
        } catch (error) {
            console.error('StationAPI.updateStation error:', error);
            throw error.response?.data || { message: '更新站點失敗，請稍後再試' };
        }
    },

    async deleteStation(equipmentId, stationId) {
        try {
            const res = await api.delete(`/equipments/${equipmentId}/stations/${stationId}`);

            return res.data;
        } catch (error) {
            console.error('StationAPI.deleteStation error:', error);
            throw error.response?.data || { message: '刪除站點失敗，請稍後再試' };
        }
    },
};