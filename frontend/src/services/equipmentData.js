import api from './axiosInstance';

export const EquipmentDataAPI = {
    async fetchEquipmentData(filterParams) {
        try {
            const res = await api.get('/data', { params: filterParams });

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '取得數據失敗，請稍後再試');
            }
        } catch (error) {
            console.error('Error fetching equipment data:', error);
            throw error.response?.data || { message: '取得數據失敗，請稍後再試' };
        }
    }
}