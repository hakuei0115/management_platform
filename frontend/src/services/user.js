import api from './axiosInstance';

export const UserAPI = {
    async fetchUserList() {
        try {
            const res = await api.get('/users');

            return res.data;
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
    }
};