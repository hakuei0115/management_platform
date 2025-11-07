import api from './axiosInstance';

export const ModelMappingsAPI = {
    async fetchModelMappings(equipmentId) {
        try {
            const response = await api.get(`/equipments/${equipmentId}/model_mappings`);

            console.log(response.data.result);
            
            return response.data.result;
        } catch (error) {
            console.error("Error fetching model mappings:", error);
            throw error.response?.data || { message: "取得模型對照表失敗，請稍後再試" };
        }
    },

    async insertModelMapping(equipmentId, mappingData) {
        try {
            const response = await api.post(`/equipments/${equipmentId}/model_mappings`, mappingData);
            
            return response.data;
        } catch (error) {
            console.error("Error inserting model mapping:", error);
            throw error.response?.data || { message: "新增模型對照表失敗，請稍後再試" };
        }
    },

    async updateModelMapping(equipmentId, mappingId, mappingData) {
        try {
            const response = await api.put(`/equipments/${equipmentId}/model_mappings/${mappingId}`, mappingData);

            return response.data;
        } catch (error) {
            console.error("Error updating model mapping:", error);
            throw error.response?.data || { message: "更新模型對照表失敗，請稍後再試" };
        }
    },

    async deleteModelMapping(equipmentId, mappingId) {
        try {
            const response = await api.delete(`/equipments/${equipmentId}/model_mappings/${mappingId}`);
            
            return response.data;
        } catch (error) {
            console.error("Error deleting model mapping:", error);
            throw error.response?.data || { message: "刪除模型對照表失敗，請稍後再試" };
        }
    }
};
