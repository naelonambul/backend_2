<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const router = useRouter()
const form = ref({ title: '', contents: '' })
const loading = ref(false)
const error = ref('')

async function submitBoard() {
  loading.value = true
  error.value = ''
  try {
    const board = await createApiClient().registerBoard({ ...form.value })
    await router.push({ name: 'board-detail', params: { idx: board.idx } })
  } catch (requestError) {
    error.value = requestError.message || '게시글을 저장하지 못했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="write-page">
    <div class="page-heading wide-heading">
      <span class="eyebrow"><i></i> WRITE A NOTE</span>
      <h1>새로운 기록을<br /><em>남겨보세요.</em></h1>
      <p>제목과 내용을 작성하면 노트 보관함에 저장됩니다.</p>
    </div>

    <PageSkeleton v-if="loading" variant="write" compact />
    <article v-else class="form-card write-card">
      <div class="form-card-top"><div><span class="section-kicker">NEW POST</span><h2>게시글 작성</h2></div><span class="route-index">03 / 05</span></div>
      <form class="api-form" @submit.prevent="submitBoard">
        <label>제목<input v-model.trim="form.title" name="title" placeholder="게시글 제목을 입력하세요" required maxlength="200" /></label>
        <label>내용<textarea v-model.trim="form.contents" name="contents" rows="10" placeholder="기억하고 싶은 이야기를 적어보세요." required></textarea></label>
        <div class="write-actions"><RouterLink class="quiet-link" :to="{ name: 'board-list' }">목록으로</RouterLink><button class="primary-button" type="submit">게시글 저장 <span>↗</span></button></div>
      </form>
      <p v-if="error" class="form-message error" role="alert">{{ error }}</p>
    </article>
  </section>
</template>
