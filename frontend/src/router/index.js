import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: { name: 'property-list' } },
    { path: '/properties', name: 'property-list', component: () => import('../views/PropertyListPage.vue') },
    { path: '/properties/new', name: 'property-create', component: () => import('../views/PropertyCreatePage.vue') },
    { path: '/properties/purchase/return', name: 'property-purchase-return', component: () => import('../views/PropertyPurchaseReturnPage.vue') },
    { path: '/properties/:idx', name: 'property-detail', component: () => import('../views/PropertyDetailPage.vue') },
    { path: '/boards', name: 'board-list', component: () => import('../views/BoardListPage.vue') },
    { path: '/boards/new', name: 'board-create', component: () => import('../views/BoardCreatePage.vue') },
    { path: '/boards/:idx', name: 'board-detail', component: () => import('../views/BoardDetailPage.vue') },
    { path: '/questions', name: 'question-list', component: () => import('../views/QuestionListPage.vue') },
    { path: '/questions/new', name: 'question-create', component: () => import('../views/QuestionCreatePage.vue') },
    { path: '/questions/:id', name: 'question-detail', component: () => import('../views/QuestionDetailPage.vue') },
    { path: '/login', name: 'login', component: () => import('../views/LoginPage.vue') },
    { path: '/auth/kakao/callback', name: 'kakao-callback', component: () => import('../views/KakaoCallbackPage.vue') },
    { path: '/signup', name: 'signup', component: () => import('../views/SignupPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: { name: 'property-list' } },
  ],
  scrollBehavior() {
    return { top: 0, behavior: 'smooth' }
  },
})

export default router
