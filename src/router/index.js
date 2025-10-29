import { createRouter, createWebHistory } from 'vue-router'


const EquipmentPage = () => import('../pages/EquipmentPage.vue')
const OperationPage = () => import('../pages/OperationPage.vue')

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/management_platform/', redirect: '/management_platform/equipment' },
    { path: '/management_platform/equipment', component: EquipmentPage, meta: { title: '設備管理' } },
    { path: '/management_platform/operation', component: OperationPage, meta: { title: '操作管理' } },
  ],
})