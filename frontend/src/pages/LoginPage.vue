<template>
    <div class="login-container">
        <el-card class="login-card">
            <h2 class="title">過濾調壓器製造數據管理平台</h2>
            <el-form :model="form" ref="formRef" :rules="rules" label-width="80px" @keydown.enter="onLogin">
                <el-form-item label="帳號" prop="username">
                    <el-input v-model="form.username" placeholder="輸入帳號" />
                </el-form-item>

                <el-form-item label="密碼" prop="password">
                    <el-input v-model="form.password" placeholder="輸入密碼" show-password />
                </el-form-item>

                <el-form-item>
                    <el-button type="primary" @click="onLogin" style="width:100%">登入</el-button>
                </el-form-item>
            </el-form>
        </el-card>
    </div>
</template>

<script setup>
import { ref } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import Swal from "sweetalert2"

const router = useRouter()
const auth = useAuthStore()

const formRef = ref()
const form = ref({ username: "", password: "" })
const rules = {
    username: [{ required: true, message: "請輸入帳號", trigger: "blur" }],
    password: [{ required: true, message: "請輸入密碼", trigger: "blur" }],
}

async function onLogin() {
    formRef.value.validate(async (valid) => {
        if (!valid) return

        const response = await auth.login(form.value.username, form.value.password);

        if (response.success) {
            Swal.fire({
                icon: 'success',
                title: '登入成功',
                showConfirmButton: false,
                timer: 1500
            });
            router.push("/dashboard")
        } else {
            Swal.fire({
                icon: 'error',
                title: '登入失敗',
                text: '請檢查帳號密碼是否正確',
            });
            form.value.username = '';
            form.value.password = '';
        }
    })
}
</script>

<style scoped>
.login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background: #f5f7fa;
}

.login-card {
    width: 360px;
    padding: 20px 30px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.title {
    text-align: center;
    margin-bottom: 20px;
}
</style>
