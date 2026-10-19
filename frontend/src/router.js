import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'

export const isNavigating = ref(false)

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: { name: 'board-list' } },
    { path: '/signup', name: 'signup', component: () => import('./pages/SignupPage.vue') },
    { path: '/login', name: 'login', component: () => import('./pages/LoginPage.vue') },
    { path: '/boards', name: 'board-list', component: () => import('./pages/BoardListPage.vue') },
    { path: '/boards/new', name: 'board-create', component: () => import('./pages/BoardCreatePage.vue') },
    { path: '/boards/:idx', name: 'board-detail', component: () => import('./pages/BoardDetailPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: { name: 'board-list' } },
  ],
  scrollBehavior() {
    return { top: 0, behavior: 'smooth' }
  },
})

let skeletonTimer

router.beforeEach((to, from) => {
  if (from.matched.length && to.fullPath !== from.fullPath) {
    window.clearTimeout(skeletonTimer)
    isNavigating.value = true
  }
})

router.afterEach(() => {
  window.clearTimeout(skeletonTimer)
  skeletonTimer = window.setTimeout(() => {
    isNavigating.value = false
  }, 260)
})

router.onError(() => {
  window.clearTimeout(skeletonTimer)
  isNavigating.value = false
})

export default router
