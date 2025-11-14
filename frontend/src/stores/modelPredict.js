import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ModelPredictAPI } from '@/services/modelPredict'

export const useModelPredictStore = defineStore('modelPredict', () => {
    const predictionResult = ref(null)
    const loading = ref(false)
    const error = ref(null)

    async function predictModel(ng_items) {
        loading.value = true
        error.value = null
        try {
            const res = await ModelPredictAPI.predictModel(ng_items);
            predictionResult.value = res;
        } catch (err) {
            console.error('predictModel error:', err)
            error.value = err.message || '模型預測失敗，請稍後再試'
            throw error.value // 再拋回前端組件
        } finally {
            loading.value = false
        }
    }

    return {
        predictionResult,
        loading,
        error,
        predictModel
    }
})