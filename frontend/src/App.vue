<script setup>
import { computed, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { createApiClient, getConfiguredBaseUrl, normalizeBaseUrl } from './api'
import { isNavigating } from './router'
import PageSkeleton from './components/PageSkeleton.vue'

const route = useRoute()
const serverUrl = ref(getConfiguredBaseUrl())
const connection = ref('unknown')
const checkingConnection = ref(false)
const connectionLabel = computed(() => ({
  unknown: '연결 확인 전',
  checking: '확인 중',
  connected: '연결됨',
  disconnected: '연결 실패',
}[connection.value]))

function skeletonVariant(name) {
  if (name === 'board-list') return 'list'
  if (name === 'board-detail') return 'detail'
  if (name === 'board-create') return 'write'
  return 'form'
}

async function checkConnection() {
  const base = normalizeBaseUrl(serverUrl.value)
  if (!base) {
    connection.value = 'disconnected'
    return
  }
  serverUrl.value = base
  localStorage.setItem('note-api-base', base)
  checkingConnection.value = true
  connection.value = 'checking'
  try {
    await createApiClient(base).ping()
    connection.value = 'connected'
  } catch {
    connection.value = 'disconnected'
  } finally {
    checkingConnection.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" :to="{ name: 'board-list' }" aria-label="모아 노트 게시글 목록">
        <span class="brand-mark" aria-hidden="true"><span></span><span></span><span></span></span>
        <span class="brand-copy"><strong>모아 노트</strong><small>NOTE WORKSPACE</small></span>
      </RouterLink>

      <nav class="main-nav" aria-label="주요 메뉴">
        <RouterLink :to="{ name: 'board-list' }" active-class="active">게시글 목록</RouterLink>
        <RouterLink :to="{ name: 'board-create' }" active-class="active">새 글 작성</RouterLink>
        <RouterLink :to="{ name: 'signup' }" active-class="active">회원가입</RouterLink>
        <RouterLink :to="{ name: 'login' }" active-class="active">로그인</RouterLink>
      </nav>

      <form class="server-control" @submit.prevent="checkConnection">
        <label for="server-url">API 서버</label>
        <input id="server-url" v-model="serverUrl" type="url" aria-label="API 서버 주소" />
        <button type="submit" :disabled="checkingConnection">{{ checkingConnection ? '확인 중' : '연결 확인' }}</button>
        <span class="connection-state" :class="connection"><i></i>{{ connectionLabel }}</span>
      </form>
    </header>

    <main class="site-main">
      <RouterView v-slot="{ Component, route: viewRoute }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="viewRoute.fullPath" />
        </Transition>
      </RouterView>
    </main>

    <Transition name="loader">
      <div v-if="isNavigating" class="navigation-overlay" aria-live="polite">
        <PageSkeleton :variant="skeletonVariant(route.name)" />
      </div>
    </Transition>

    <footer class="site-footer">
      <span>MOA NOTE · FASTAPI</span>
      <span>작은 기록을 모으는 공간</span>
    </footer>
  </div>
</template>
