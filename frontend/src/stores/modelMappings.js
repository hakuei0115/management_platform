import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ModelMappingsAPI } from '@/services/modelMappings'

export const useModelMappingsStore = defineStore('modelMappings', () => {
    const modelMappings = ref({})
    const loading = ref(false)
    const error = ref(null)

    async function fetchModelMappings(equipmentId) {
        loading.value = true
        error.value = null

        try {
            const response = await ModelMappingsAPI.fetchModelMappings(equipmentId);

            modelMappings.value[equipmentId] = response;
        } catch (error) {
            console.error('fetchModelMappings error:', error);
            error.value = error.message || '無法取得模型對照表';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function insertModelMapping(equipmentId, mappingData) {
        loading.value = true;
        error.value = null;

        try {
            const payload = mappingData?.value ? mappingData.value : mappingData;
            const response = await ModelMappingsAPI.insertModelMapping(equipmentId, payload);
            
            if (response.success) {
                if (!modelMappings.value[equipmentId]) modelMappings.value[equipmentId] = [];
                modelMappings.value[equipmentId].push(payload);
            } else {
                throw new Error(response.message || '新增模型對照表失敗');
            }
        } catch (error) {
            console.error('insertModelMapping error:', error);
            error.value = error.message || '無法新增模型對照表';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function updateModelMapping(equipmentId, mappingId, mappingData) {
        loading.value = true;
        error.value = null;

        try {
            const payload = mappingData?.value ? mappingData.value : mappingData;
            const response = await ModelMappingsAPI.updateModelMapping(equipmentId, mappingId, payload);

            if (response.success) {
                const index = modelMappings.value[equipmentId].findIndex(item => item.id === mappingId);
                if (index !== -1) {
                    modelMappings.value[equipmentId][index] = payload;
                }
            } else {
                throw new Error(response.message || '更新模型對照表失敗');
            }
        } catch (error) {
            console.error('updateModelMapping error:', error);
            error.value = error.message || '無法更新模型對照表';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    async function deleteModelMapping(equipmentId, mappingId) {
        loading.value = true;
        error.value = null;

        try {
            const response = await ModelMappingsAPI.deleteModelMapping(equipmentId, mappingId);

            if (response.success) {
                const index = modelMappings.value[equipmentId].findIndex(item => item.id === mappingId);
                if (index !== -1) {
                    modelMappings.value[equipmentId].splice(index, 1);
                }
            } else {
                throw new Error(response.message || '刪除模型對照表失敗');
            }
        } catch (error) {
            console.error('deleteModelMapping error:', error);
            error.value = error.message || '無法刪除模型對照表';
            throw error.value;
        } finally {
            loading.value = false;
        }
    }

    return {
        modelMappings,
        loading,
        error,
        fetchModelMappings,
        insertModelMapping,
        updateModelMapping,
        deleteModelMapping
    };
});