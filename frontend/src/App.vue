<template>
  <el-container style="height: 100vh;">
    <!-- 左側選單 -->
    <el-aside v-if="auth.isLoggedIn" width="220px">
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/dashboard">管理平台首頁</el-menu-item>
        <el-menu-item index="/equipment">設備管理</el-menu-item>
        <el-menu-item index="/operation">操作管理</el-menu-item>
        <el-menu-item index="/account">帳號管理</el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主內容區 -->
    <el-container>
      <!-- Header -->
      <el-header v-if="auth.isLoggedIn" height="56px" class="app-header">
        <div class="header-left">過濾調壓器製造數據管理平台</div>
        <div class="header-right">
          <span>{{ auth.user.name }} ({{ auth.user.role }})</span>
          <el-button type="danger" size="small" @click="logout">登出</el-button>
        </div>
      </el-header>

      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  ElMessageBox.confirm('確定要登出嗎？', '提示', { type: 'warning' }).then(() => {
    auth.logout()
    router.push('/')
  })
}
</script>

<style>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  padding: 0 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
