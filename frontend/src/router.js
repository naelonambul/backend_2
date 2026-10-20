import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: { name: 'property-list' } },
    { path: '/properties', name: 'property-list', component: () => import('./pages/PropertyListPage.vue') },
    { path: '/properties/new', name: 'property-create', component: () => import('./pages/PropertyCreatePage.vue') },
    { path: '/properties/:idx', name: 'property-detail', component: () => import('./pages/PropertyDetailPage.vue') },
    { path: '/boards', name: 'board-list', component: () => import('./pages/BoardListPage.vue') },
    { path: '/boards/new', name: 'board-create', component: () => import('./pages/BoardCreatePage.vue') },
    { path: '/boards/:idx', name: 'board-detail', component: () => import('./pages/BoardDetailPage.vue') },
    { path: '/login', name: 'login', component: () => import('./pages/LoginPage.vue') },
    { path: '/auth/kakao/callback', name: 'kakao-callback', component: () => import('./pages/KakaoCallbackPage.vue') },
    { path: '/signup', name: 'signup', component: () => import('./pages/SignupPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: { name: 'property-list' } },
  ],
  scrollBehavior() {
    return { top: 0, behavior: 'smooth' }
  },
})

export default router
