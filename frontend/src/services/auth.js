import api from './axiosInstance'

export const AuthAPI = {
    async login(email, password) {
        try {
            const res = await api.post('/login', { email, password })
            return res.data
        } catch (err) {
            console.error('AuthAPI.login error:', err)
            throw err.response?.data || { message: '登入失敗，請稍後再試' }
        }
    },
}