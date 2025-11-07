import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { jwtDecode } from 'jwt-decode'
import { AuthAPI } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
    const token = ref(sessionStorage.getItem('token') || '')
    const user = ref(token.value ? jwtDecode(token.value) : {})

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
        } catch (error) {
            return error || '登入失敗，請稍後再試。';
        }
    }

    function logout() {
        token.value = ''
        user.value = {}
        sessionStorage.removeItem('token')
    }

    return { token, user, isLoggedIn, login, logout }
})
