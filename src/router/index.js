import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const LoginPage = () => import('../pages/LoginPage.vue')
const DashboardPage = () => import('../pages/DashboardPage.vue')
const EquipmentPage = () => import('../pages/EquipmentPage.vue')
const OperationPage = () => import('../pages/OperationPage.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginPage, meta: { title: '登入' } },
    { path: '/management_platform/', component: DashboardPage, meta: { title: '管理平台首頁', requiresAuth: true } },
    { path: '/management_platform/equipment', component: EquipmentPage, meta: { title: '設備管理', requiresAuth: true } },
    { path: '/management_platform/operation', component: OperationPage, meta: { title: '操作管理', requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

// 登入驗證守衛
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && auth.isLoggedIn) {
    // ✅ 若已登入又打開 /login → 自動導向 Dashboard
    next('/management_platform/')
  } else {
    next()
  }
})

export default router