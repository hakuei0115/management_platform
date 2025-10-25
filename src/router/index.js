import { createRouter, createWebHistory } from 'vue-router'


const EquipmentPage = () => import('../pages/EquipmentPage.vue')
const OperationPage = () => import('../pages/OperationPage.vue')

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/equipment' },
    { path: '/equipment', component: EquipmentPage, meta: { title: '設備管理' } },
    { path: '/operation', component: OperationPage, meta: { title: '操作管理' } },
  ],
})