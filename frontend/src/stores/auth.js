import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { jwtDecode } from 'jwt-decode'
import { AuthAPI } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
    function safeDecode(t) {
        if (!t) return {}
        try {
            return jwtDecode(t)
        } catch {
            sessionStorage.removeItem('token')
            return {}
        }
    }

    const token = ref(sessionStorage.getItem('token') || '')
    const user = ref(safeDecode(token.value))

    const isLoggedIn = computed(() => !!token.value)

    async function login(email, password) {
        try {
            const res = await AuthAPI.login(email, password);

            if (res.success) {
                token.value = res.token;
                user.value = jwtDecode(res.token);
                sessionStorage.setItem('token', token.value);
                return res;
            }
            return res;
        } catch (error) {
            return error || { success: false, message: '登入失敗，請稍後再試。' };
        }
    }

    function logout() {
        token.value = ''
        user.value = {}
        sessionStorage.removeItem('token')
    }

    return { token, user, isLoggedIn, login, logout }
})
