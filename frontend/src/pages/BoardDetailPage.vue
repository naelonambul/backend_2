<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import { noteTone } from '../lib/notes'

const route = useRoute()
const board = ref(null)
const loading = ref(true)
const error = ref('')

async function loadNote() {
  loading.value = true
  error.value = ''
  try {
    board.value = await createApiClient().readBoard(route.params.idx)
  } catch (requestError) {
    error.value = requestError.message || '기록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(loadNote)
</script>

<template>
  <section class="detail-page" aria-labelledby="detail-title">
    <div class="detail-toolbar">
      <RouterLink class="back-link" :to="{ name: 'board-list' }"><span aria-hidden="true">←</span> 보관함</RouterLink>
      <RouterLink class="button-secondary" :to="{ name: 'board-create' }">새 기록 <span aria-hidden="true">↗</span></RouterLink>
    </div>

    <div v-if="loading" class="detail-loading" aria-busy="true" aria-label="기록을 불러오는 중">
      <div class="detail-loading__line"></div>
      <div class="detail-loading__line detail-loading__line--title"></div>
      <div class="detail-loading__block"></div>
    </div>

    <div v-else-if="error" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span>
      <h2>기록을 찾지 못했어요.</h2>
      <p>{{ error }}</p>
      <RouterLink class="button-secondary" :to="{ name: 'board-list' }">보관함으로 돌아가기</RouterLink>
    </div>

    <article v-else-if="board" class="detail-sheet" :class="'detail-sheet--' + noteTone(board.idx)">
      <div class="detail-sheet__top">
        <span>모아 둔 기록</span>
        <span>No. {{ String(board.idx).padStart(3, '0') }}</span>
      </div>
      <h1 id="detail-title">{{ board.title }}</h1>
      <div class="detail-sheet__rule"><span aria-hidden="true">✳</span></div>
      <p class="detail-content">{{ board.contents }}</p>
      <div class="detail-sheet__bottom">
        <span>{{ board.contents.trim().length }}자</span>
        <RouterLink class="detail-sheet__next" :to="{ name: 'board-create' }">다음 기록 남기기 <span aria-hidden="true">↗</span></RouterLink>
      </div>
    </article>
  </section>
</template>
