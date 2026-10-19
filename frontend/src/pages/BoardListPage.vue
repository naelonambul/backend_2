<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createApiClient } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const boards = ref([])
const loading = ref(true)
const error = ref('')

async function loadBoards() {
  loading.value = true
  error.value = ''
  try {
    boards.value = await createApiClient().listBoards()
  } catch (requestError) {
    error.value = requestError.message || '게시글 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

function excerpt(contents) {
  return contents.length > 150 ? `${contents.slice(0, 150)}…` : contents
}

onMounted(loadBoards)
</script>

<template>
  <section class="list-page">
    <div class="page-heading list-heading">
      <div>
        <span class="eyebrow"><i></i> YOUR NOTE LIBRARY</span>
        <h1>모아둔 기록을<br /><em>다시 꺼내보세요.</em></h1>
        <p>게시글을 열어 내용을 확인하거나 새 기록을 추가할 수 있어요.</p>
      </div>
      <RouterLink class="primary-button heading-button" :to="{ name: 'board-create' }">새 글 작성 <span>↗</span></RouterLink>
    </div>

    <PageSkeleton v-if="loading" variant="list" compact />
    <div v-else-if="error" class="state-card error-state" role="alert">
      <span class="state-ornament">!</span><h2>목록을 불러오지 못했어요.</h2><p>{{ error }}</p>
      <button class="secondary-button" type="button" @click="loadBoards">다시 시도</button>
    </div>
    <div v-else-if="boards.length" class="board-list" aria-live="polite">
      <RouterLink v-for="(board, index) in boards" :key="board.idx" class="board-card" :style="{ '--card-index': index }" :to="{ name: 'board-detail', params: { idx: board.idx } }">
        <div class="board-card-meta"><span class="board-number">NO. {{ String(board.idx).padStart(3, '0') }}</span><span class="board-arrow">↗</span></div>
        <h2>{{ board.title }}</h2>
        <p>{{ excerpt(board.contents) }}</p>
        <span class="read-link">내용 보기 <b>→</b></span>
      </RouterLink>
    </div>
    <div v-else class="state-card empty-state">
      <span class="empty-note-mark">✳</span><span class="section-kicker">A FRESH PAGE</span>
      <h2>아직 작성한 게시글이 없어요.</h2><p>첫 기록을 남기고 이곳에 차곡차곡 모아보세요.</p>
      <RouterLink class="primary-button" :to="{ name: 'board-create' }">첫 게시글 작성 <span>↗</span></RouterLink>
    </div>

    <div v-if="!loading && !error && boards.length" class="list-footnote"><span>전체 게시글</span><strong>{{ boards.length }}</strong><button type="button" @click="loadBoards">새로고침 ↻</button></div>
  </section>
</template>
