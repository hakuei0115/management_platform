import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import Swal from 'sweetalert2';

const api = axios.create({
    baseURL: 'http://localhost:3000/api',
    timeout: 10000,
})

api.interceptors.request.use((config) => {
    const token = sessionStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    (response) => response,
    (error) => {
        const auth = useAuthStore()

        if (error.response && [401, 403].includes(error.response.status)) {
            console.warn('Token 已失效，自動登出')
            auth.logout();
            Swal.fire('錯誤', '登入已過期，請重新登入', 'warning');
        }

        return Promise.reject(error)
    }
)

export default api
