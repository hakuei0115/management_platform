import api from './axiosInstance';

export const StationAPI = {
    async fetchStationList(equipmentId) {
        try {
            const res = await api.get(`/equipments/${equipmentId}/stations`);
            return res.data;
        } catch (error) {
            console.error('StationAPI.fetchStationList error:', error);
            throw error.response?.data || { message: '取得站點列表失敗，請稍後再試' };
        }
    },

    async insertStation(stationData) {
        try {
            const res = await api.post('/stations', stationData);

            return res.data;
        } catch (error) {
            console.error('StationAPI.insertStation error:', error);
            throw error.response?.data || { message: '新增站點失敗，請稍後再試' };
        }
    },

    async updateStation(stationId, stationData) {
        try {
            const res = await api.put(`/stations/${stationId}`, stationData);

            return res.data;
        } catch (error) {
            console.error('StationAPI.updateStation error:', error);
            throw error.response?.data || { message: '更新站點失敗，請稍後再試' };
        }
    },

    async deleteStation(stationId) {
        try {
            const res = await api.delete(`/stations/${stationId}`);

            return res.data;
        } catch (error) {
            console.error('StationAPI.deleteStation error:', error);
            throw error.response?.data || { message: '刪除站點失敗，請稍後再試' };
        }
    },
};