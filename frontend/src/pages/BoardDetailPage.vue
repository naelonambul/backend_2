<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const route = useRoute()
const board = ref(null)
const loading = ref(true)
const error = ref('')

async function loadBoard() {
  loading.value = true
  error.value = ''
  try {
    board.value = await createApiClient().readBoard(route.params.idx)
  } catch (requestError) {
    error.value = requestError.message || '게시글을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(loadBoard)
</script>

<template>
  <section class="detail-page">
    <div class="detail-back"><RouterLink :to="{ name: 'board-list' }"><span>←</span> 게시글 목록</RouterLink><RouterLink class="new-post-link" :to="{ name: 'board-create' }">새 글 작성 <span>↗</span></RouterLink></div>

    <PageSkeleton v-if="loading" variant="detail" compact />
    <div v-else-if="error" class="state-card error-state" role="alert">
      <span class="state-ornament">!</span><h2>게시글을 찾을 수 없어요.</h2><p>{{ error }}</p>
      <RouterLink class="secondary-button" :to="{ name: 'board-list' }">목록으로 돌아가기</RouterLink>
    </div>
    <article v-else-if="board" class="detail-card">
      <div class="detail-meta"><span class="section-kicker">NOTE DETAIL</span><span class="board-number">NO. {{ String(board.idx).padStart(3, '0') }}</span></div>
      <h1>{{ board.title }}</h1>
      <div class="detail-divider"><span>✳</span></div>
      <p class="detail-content">{{ board.contents }}</p>
      <div class="detail-actions"><RouterLink class="quiet-link" :to="{ name: 'board-list' }">← 목록으로 돌아가기</RouterLink><RouterLink class="primary-button" :to="{ name: 'board-create' }">새 기록 작성 <span>↗</span></RouterLink></div>
    </article>
  </section>
</template>
