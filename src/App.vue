<template>
  <el-container style="height: 100vh;">
    <el-aside width="220px">
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/equipment">設備管理</el-menu-item>
        <el-menu-item index="/operation">操作管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header height="56px" class="app-header">智能數據管理平台</el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>


<style>
.app-header {
  display: flex;
  align-items: center;
  font-weight: 600;
}
</style>