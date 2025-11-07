import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import Swal from 'sweetalert2';

const LoginPage = () => import('@/pages/LoginPage.vue');
const DashboardPage = () => import('@/pages/DashboardPage.vue');
const EquipmentPage = () => import('@/pages/EquipmentPage.vue');
const OperationPage = () => import('@/pages/OperationPage.vue');
const AccountPage = () => import('@/pages/AccountPage.vue');

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginPage, meta: { title: '登入' } },
    { path: '/dashboard', component: DashboardPage, meta: { title: '首頁', requiresAuth: true } },
    { path: '/equipment', component: EquipmentPage, meta: { title: '設備管理', requiresAuth: true } },
    { path: '/operation', component: OperationPage, meta: { title: '操作管理', requiresAuth: true } },
    { path: '/account', component: AccountPage, meta: { title: '帳號管理', requiresAuth: true, adminOnly: true } },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
});

// ✅ 統一守衛
router.beforeEach((to, from, next) => {
  const auth = useAuthStore();

  // 未登入禁止進入
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    Swal.fire({
      icon: 'warning',
      title: '請先登入',
      showConfirmButton: false,
      timer: 1500
    });
    return next('/login');
  }

  // 已登入但進登入頁 → 回首頁
  if (to.path === '/login' && auth.isLoggedIn) {
    return next('/dashboard');
  }

  // 非管理員進帳號管理 → 回首頁
  if (to.meta.adminOnly && auth.user.role !== 'admin') {
    Swal.fire({
      icon: 'error',
      title: '權限不足',
      text: '您沒有權限訪問此頁面',
      showConfirmButton: false,
      timer: 1500
    });
    return next('/dashboard');
  }

  next();
});

export default router;
