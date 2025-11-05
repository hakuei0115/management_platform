import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { jwtDecode } from 'jwt-decode'
import { AuthAPI } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(sessionStorage.getItem('token') || '')
    const user = ref(token.value ? jwtDecode(token.value) : {})

    const isLoggedIn = computed(() => !!token.value)

    async function login(email, password) {
        const res = await AuthAPI.login(email, password);

        if (res.message === '登入成功') {
            token.value = res.token
            user.value = jwtDecode(res.token)
            sessionStorage.setItem('token', token.value)
            return true
        }
        return false
    }

    function logout() {
        token.value = ''
        user.value = {}
        sessionStorage.removeItem('token')
    }

    return { token, user, isLoggedIn, login, logout }
})
