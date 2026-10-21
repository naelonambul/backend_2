<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api/api.js'

const router = useRouter()
const form = ref({ title: '', contents: '' })
const submitting = ref(false)
const error = ref('')

async function submitNote() {
  error.value = ''
  submitting.value = true
  try {
    const note = await createApiClient().registerBoard({
      title: form.value.title.trim(),
      contents: form.value.contents.trim(),
    })
    await router.push({ name: 'board-detail', params: { idx: note.idx } })
  } catch (requestError) {
    error.value = requestError.message || '기록을 저장하지 못했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="editor-page" aria-labelledby="editor-title">
    <RouterLink class="back-link" :to="{ name: 'board-list' }"><span aria-hidden="true">←</span> 보관함으로</RouterLink>

    <div class="editor-heading">
      <p class="section-label">새 기록</p>
      <h1 id="editor-title">기억하고 싶은 장면을<br />천천히 적어 보세요.</h1>
      <p>짧은 문장 하나도 이곳에 오래 남겨둘 수 있어요.</p>
    </div>

    <form class="editor-sheet" @submit.prevent="submitNote">
      <div class="editor-sheet__top">
        <span class="editor-sheet__dot" aria-hidden="true"></span>
        <span>새 페이지</span>
        <span class="editor-sheet__date">지금 쓰는 중</span>
      </div>

      <label class="field-label" for="note-title">제목</label>
      <input
        id="note-title"
        v-model="form.title"
        class="editor-title-input"
        name="title"
        type="text"
        maxlength="200"
        placeholder="무엇을 기억하고 싶나요?"
        autocomplete="off"
        required
      />

      <label class="field-label" for="note-contents">내용</label>
      <textarea
        id="note-contents"
        v-model="form.contents"
        class="editor-body-input"
        name="contents"
        rows="10"
        placeholder="떠오르는 생각을 편하게 적어 보세요."
        required
      ></textarea>

      <div class="editor-footer">
        <span>{{ form.contents.length }}자</span>
        <div class="editor-actions">
          <RouterLink class="button-secondary" :to="{ name: 'board-list' }">취소</RouterLink>
          <button class="button-primary" type="submit" :disabled="submitting">
            {{ submitting ? '저장 중…' : '기록 저장' }} <span aria-hidden="true">↗</span>
          </button>
        </div>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    </form>
  </section>
</template>
