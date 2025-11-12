import { defineStore } from 'pinia'
import { ref } from 'vue'
import { UserAPI } from '@/services/user'

export const useUserStore = defineStore('user', () => {
    const userList = ref([])
    const roles = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function fetchUsers() {
        loading.value = true
        error.value = null

        try {
            const res = await UserAPI.fetchUserList()
            const rolesRes = await UserAPI.getRoles()

            if (rolesRes.length !== 0) {
                roles.value = rolesRes;
            } else {
                roles.value = [];
            }

            if (res.length !== 0) {
                userList.value = res;
            } else {
                userList.value = [];
            }
        } catch (err) {
            console.error('fetchUsers error:', err)
            error.value = err.message || '無法取得使用者列表'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    async function insertUser(userData) {
        loading.value = true
        error.value = null

        try {
            const payload = userData?.value ? userData.value : userData
            const res = await UserAPI.insertUser(payload)

            if (res.success) {
                // 有成功，手動更新前端 userList
                userList.value.push(payload)
            } else {
                throw new Error(res.message || '新增使用者失敗')
            }

            return res
        } catch (err) {
            console.error('insertUser error:', err)
            error.value = err.message || '新增使用者時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    async function updateUser(userId, userData) {
        loading.value = true
        error.value = null

        try {
            const payload = userData?.value ? userData.value : userData
            const res = await UserAPI.updateUser(userId, payload)

            if (res.success) {
                const index = userList.value.findIndex(u => u.id === userId)
                if (index !== -1) {
                    userList.value[index] = { ...userList.value[index], ...payload }
                }
            } else {
                throw new Error(res.message || '更新使用者失敗')
            }

            return res
        } catch (err) {
            console.error('updateUser error:', err)
            error.value = err.message || '更新使用者時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    async function deleteUser(userId) {
        loading.value = true
        error.value = null

        try {
            const res = await UserAPI.deleteUser(userId)

            if (res.success) {
                userList.value = userList.value.filter(u => u.id !== userId)
            } else {
                throw new Error(res.message || '刪除使用者失敗')
            }

            return res
        } catch (err) {
            console.error('deleteUser error:', err)
            error.value = err.message || '刪除使用者時發生錯誤'
            throw error.value
        } finally {
            loading.value = false
        }
    }

    function getRoleIdByName(roleName) {
        const role = roles.value.find(r => r.name === roleName);
        
        return role ? role.id : null
    }

    return {
        userList,
        loading,
        error,
        fetchUsers,
        insertUser,
        updateUser,
        deleteUser,
        getRoleIdByName,
    }
})
