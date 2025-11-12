import api from './axiosInstance';

export const UserAPI = {
    async fetchUserList() {
        try {
            const res = await api.get('/users');

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '取得使用者列表失敗，請稍後再試');
            }
        } catch (error) {
            console.error('Error fetching user list:', error);

            throw error;
        }
    },

    async insertUser(userData) {
        try {
            const res = await api.post('/users', userData);
            return res.data;
        } catch (error) {
            console.error('Error inserting user:', error);
            throw error;
        }
    },

    async updateUser(userId, userData) {
        try {
            const res = await api.put(`/users/${userId}`, userData);
            return res.data;
        } catch (error) {
            console.error('Error updating user:', error);
            throw error;
        }
    },

    async deleteUser(userId) {
        try {
            const res = await api.delete(`/users/${userId}`);
            return res.data;
        } catch (error) {
            console.error('Error deleting user:', error);
            throw error;
        }
    },

    async getRoles() {
        try {
            const res = await api.get('/roles');

            if (res.data.success) {
                return res.data.data;
            } else {
                throw new Error(res.data.message || '取得角色列表失敗，請稍後再試');
            }
        } catch (error) {
            console.error('Error fetching user roles:', error);

            throw error;
        }
    }
};