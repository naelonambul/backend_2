<script setup>
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { createApiClient } from './api/api.js'
import { currentUser, refreshCurrentUser } from './stores/auth/session.js'

const route = useRoute()
const isAuthPage = computed(() => route.name === 'login' || route.name === 'signup' || route.name === 'kakao-callback')
const api = createApiClient()

watch(() => route.fullPath, () => {
  refreshCurrentUser(api).catch(() => {})
}, { immediate: true })
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <RouterLink class="brand" :to="{ name: 'property-list' }" aria-label="하벤 홈">
          <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 36 36" fill="none"><path d="m5 17 13-11 13 11v14H5V17Z" fill="currentColor"/><path d="M14 31V19h8v12M5 17l13-11 13 11" stroke="#F4F7F5" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
          <span class="brand-name">하벤<span> 홈</span></span>
        </RouterLink>
        <nav class="header-nav" aria-label="주요 메뉴"><RouterLink :to="{ name: 'property-list' }">매물 둘러보기</RouterLink><RouterLink :to="{ name: 'question-list' }">질문 게시판</RouterLink><RouterLink :to="{ name: 'login' }">{{ currentUser?.name || '로그인' }}</RouterLink></nav>
        <RouterLink class="header-question-mobile" :to="{ name: 'question-list' }">질문 게시판</RouterLink>
        <RouterLink class="header-create" :to="{ name: 'property-create' }"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12" /></svg><span>매물 등록</span></RouterLink>
      </div>
    </header>
    <main class="main-content" :class="{ 'main-content--auth': isAuthPage }"><RouterView v-slot="{ Component }"><Transition name="page" mode="out-in"><component :is="Component" /></Transition></RouterView></main>
    <footer class="site-footer"><RouterLink class="footer-brand" :to="{ name: 'property-list' }">하벤 홈</RouterLink><span>새로운 시작을 위한 집을 만나보세요.</span><span class="footer-copy">나에게 맞는 공간을 천천히 찾아보세요.</span></footer>
  </div>
</template>
