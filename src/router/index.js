import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const LoginPage = () => import('../pages/LoginPage.vue')
const DashboardPage = () => import('../pages/DashboardPage.vue')
const EquipmentPage = () => import('../pages/EquipmentPage.vue')
const OperationPage = () => import('../pages/OperationPage.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: LoginPage, meta: { title: '登入' } },
    { path: '/dashboard', component: DashboardPage, meta: { title: '管理平台首頁', requiresAuth: true } },
    { path: '/equipment', component: EquipmentPage, meta: { title: '設備管理', requiresAuth: true } },
    { path: '/operation', component: OperationPage, meta: { title: '操作管理', requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// 登入驗證守衛
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
  } else if (to.path === '/' && auth.isLoggedIn) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router