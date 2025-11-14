import api from './axiosInstance';

export const ModelPredictAPI = {
    async predictModel(ng_items) {
        try {
            const res = await api.post('http://localhost:5000/predict', { ng_items });

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