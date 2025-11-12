import api from './axiosInstance';

export const EquipmentAPI = {
    async fetchEquipmentList() {
        try {
            const res = await api.get('/equipments');

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '取得設備列表失敗，請稍後再試');
            }
        } catch (err) {
            console.error('EquipmentAPI.fetchEquipmentList error:', err);
            throw err.response?.data || { message: '取得設備列表失敗，請稍後再試' };
        }
    },

    async insertEquipment(equipmentData) {
        try {
            const res = await api.post('/equipments', equipmentData);

            return res.data;
        } catch (err) {
            console.error('EquipmentAPI.insertEquipment error:', err);
            throw err.response?.data || { message: '新增設備失敗，請稍後再試' };
        }
    },

    async updateEquipment(equipmentId, equipmentData) {
        try {
            const res = await api.put(`/equipments/${equipmentId}`, equipmentData);
            
            return res.data;
        } catch (err) {
            console.error('EquipmentAPI.updateEquipment error:', err);
            throw err.response?.data || { message: '更新設備失敗，請稍後再試' };
        }
    },

    async deleteEquipment(equipmentId) {
        try {
            const res = await api.delete(`/equipments/${equipmentId}`);

            return res.data;;
        } catch (err) {
            console.error('EquipmentAPI.deleteEquipment error:', err);
            throw err.response?.data || { message: '刪除設備失敗，請稍後再試' };
        }
    },
}