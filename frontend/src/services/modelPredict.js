import api from './axiosInstance';

export const ModelPredictAPI = {
    async predictModel(ng_items, station_id = 'default_station', leak_values = {}) {
        try {
            const targetUrl = import.meta.env.VITE_MODEL_API_URL || '/model/predict';
            const res = await api.post(targetUrl, {
                ng_items,
                station_id,
                leak_values
            });

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '模型預測失敗，請稍後再試');
            }
        } catch (error) {
            console.error('Error predicting model:', error);
            throw error.response?.data || { message: '模型預測失敗，請稍後再試' };
        }
    }
}
