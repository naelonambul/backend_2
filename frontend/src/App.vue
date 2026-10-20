<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const isAuthPage = computed(() => route.name === 'login' || route.name === 'signup' || route.name === 'kakao-callback')
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <RouterLink class="brand" :to="{ name: 'board-list' }" aria-label="모아 노트 보관함">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 36 36" fill="none">
              <path d="M9 8.5c0-.83.67-1.5 1.5-1.5h17c.83 0 1.5.67 1.5 1.5v20.2a.8.8 0 0 1-1.2.69L19 24.7l-8.8 4.69a.8.8 0 0 1-1.2-.69V8.5Z" fill="currentColor" />
              <path d="M14 13h10M14 17h7" stroke="#F4F7F5" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>
          <span class="brand-name">모아 노트</span>
        </RouterLink>

        <nav class="header-nav" aria-label="주요 메뉴">
          <RouterLink :to="{ name: 'board-list' }">보관함</RouterLink>
          <RouterLink :to="{ name: 'login' }">로그인</RouterLink>
        </nav>

        <RouterLink class="header-create" :to="{ name: 'board-create' }">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M10 4v12M4 10h12" />
          </svg>
          <span>새 기록</span>
        </RouterLink>
      </div>
    </header>

    <main class="main-content" :class="{ 'main-content--auth': isAuthPage }">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <footer class="site-footer">
      <RouterLink class="footer-brand" :to="{ name: 'board-list' }">모아 노트</RouterLink>
      <span>작은 기록도 다시 만날 수 있도록.</span>
      <span class="footer-copy">기록은 이 기기에서 시작됩니다.</span>
    </footer>
  </div>
</template>
