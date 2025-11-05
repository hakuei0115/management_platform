import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:3001/api',
    timeout: 10000,
})

// 攔截器：自動加上 JWT Token
api.interceptors.request.use((config) => {
    const token = sessionStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

export default api
