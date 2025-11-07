<template>
    <el-card class="account-page">
        <div class="toolbar">
            <el-button type="primary" @click="addUsers()">新增使用者</el-button>
        </div>

        <el-table :data="userList" border style="width: 100%">
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="email" label="Email" />
            <el-table-column prop="role" label="角色" width="120">
                <template #default="{ row }">
                    <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">{{ row.role }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="220">
                <template #default="{ row }">
                    <el-button size="small" @click="updateUsers(row.id)">編輯</el-button>
                    <el-popconfirm title="確定刪除此使用者？" @confirm="deleteUser(row.id)">
                        <template #reference>
                            <el-button size="small" type="danger">刪除</el-button>
                        </template>
                    </el-popconfirm>
                </template>
            </el-table-column>
        </el-table>

        <el-dialog v-model="dialogVisible" :title="editingUser ? '編輯使用者' : '新增使用者'">
            <el-form :model="form" label-width="100px">
                <el-form-item label="Email">
                    <el-input v-model="form.email" />
                </el-form-item>
                <el-form-item label="角色">
                    <el-select v-model="form.role" placeholder="選擇角色">
                        <el-option label="管理員" value="admin" />
                        <el-option label="一般使用者" value="user" />
                    </el-select>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="dialogVisible = false">取消</el-button>
                <el-button type="primary" @click="submitForm">儲存</el-button>
            </template>
        </el-dialog>
    </el-card>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";

const userStore = useUserStore();
const dialogVisible = ref(false);
const editingUser = ref(null);
const form = ref({ email: "", role: "user" });

onMounted(() => userStore.fetchUsers());
const userList = userStore.userList;

function openForm(user = null) {
    editingUser.value = user;
    form.value = user ? { ...user } : { email: "", role: "user" };
    dialogVisible.value = true;
}

async function submitForm() {
    if (editingUser.value) {
        await userStore.updateUser(editingUser.value.id, form.value);
        ElMessage.success("使用者更新成功");
    } else {
        await userStore.createUser(form.value);
        ElMessage.success("使用者新增成功");
    }
    dialogVisible.value = false;
}

async function deleteUser(id) {
    await userStore.deleteUser(id);
    ElMessage.success("使用者已刪除");
}
</script>

<style scoped>
.account-page {
    font-size: 15px;
}

.toolbar {
    margin-bottom: 12px;
    text-align: right;
}
</style>
