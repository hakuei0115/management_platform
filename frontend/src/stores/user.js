import { defineStore } from 'pinia'
import { ref } from 'vue'
import { UserAPI } from '@/services/user'

export const useUserStore = defineStore('user', () => {
    const userList = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function fetchUsers() {
        loading.value = true
        error.value = null

        try {
            const res = await UserAPI.fetchUserList()
            if (res.length !== 0) {
                userList.value = res.users || []
            } else {
                throw new Error(res.message || '取得使用者列表失敗')
            }
        } catch (error) {
            console.error('fetchUsers error:', error);
            error.value = error.message || '無法取得使用者列表'
            throw error.value // 再拋回前端組件
        } finally {
            loading.value = false
        }
    }

    return {
        userList,
        loading,
        error,
        fetchUsers
    }
})