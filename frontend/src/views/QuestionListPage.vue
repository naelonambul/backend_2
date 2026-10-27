<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createApiClient } from '../api/api.js'

const questions = ref([])
const loading = ref(true)
const error = ref('')
const query = ref('')
const visibleQuestions = computed(() => {
  const normalized = query.value.trim().toLocaleLowerCase()
  if (!normalized) return questions.value
  return questions.value.filter((question) =>
    `${question.title} ${question.contents}`.toLocaleLowerCase().includes(normalized),
  )
})

async function loadQuestions() {
  loading.value = true
  error.value = ''
  try {
    questions.value = await createApiClient().listQuestions()
  } catch (requestError) {
    error.value = requestError.message || '질문을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

function excerpt(contents) {
  const text = (contents || '').trim()
  return text.length > 118 ? `${text.slice(0, 115)}…` : text
}

onMounted(loadQuestions)
</script>

<template>
  <section class="questions-page" aria-labelledby="questions-title">
    <div class="questions-heading">
      <div>
        <p class="section-label">함께 나누는 질문</p>
        <h1 id="questions-title">궁금한 점을 편하게 물어보세요.</h1>
        <p>사진 한 장을 곁들여 질문하고, 한 곳에 답변을 남길 수 있어요.</p>
      </div>
      <RouterLink class="button-primary" :to="{ name: 'question-create' }">질문 작성 <span aria-hidden="true">↗</span></RouterLink>
    </div>

    <div class="questions-tools">
      <label class="questions-search">
        <span class="visually-hidden">질문 검색</span>
        <input v-model="query" type="search" placeholder="질문 제목이나 내용 검색" />
      </label>
      <span class="questions-count">질문 {{ questions.length }}개</span>
    </div>

    <div v-if="loading" class="question-list" aria-busy="true" aria-label="질문을 불러오는 중">
      <div v-for="item in 3" :key="item" class="question-skeleton"></div>
    </div>
    <div v-else-if="error" class="empty-panel empty-panel--error" role="alert">
      <h2>질문을 가져오지 못했어요.</h2>
      <p>{{ error }}</p>
      <button class="text-button" type="button" @click="loadQuestions">다시 불러오기</button>
    </div>
    <div v-else-if="visibleQuestions.length" class="question-list" aria-live="polite">
      <RouterLink v-for="question in visibleQuestions" :key="question.id" class="question-row" :to="{ name: 'question-detail', params: { id: question.id } }">
        <img v-if="question.image_url" class="question-row__image" :src="question.image_url" :alt="`${question.title} 첨부 이미지`" />
        <div class="question-row__main">
          <div class="question-row__meta">
            <span>질문 {{ String(question.id).padStart(3, '0') }}</span>
            <span class="question-status" :class="{ 'question-status--answered': question.answer }">{{ question.answer ? '답변 완료' : '답변 기다리는 중' }}</span>
          </div>
          <h2>{{ question.title }}</h2>
          <p>{{ excerpt(question.contents) }}</p>
        </div>
        <span class="question-row__arrow" aria-hidden="true">↗</span>
      </RouterLink>
    </div>
    <div v-else class="empty-panel">
      <span class="empty-panel__symbol" aria-hidden="true">?</span>
      <h2>{{ query.trim() ? '검색 결과가 없어요.' : '아직 등록된 질문이 없어요.' }}</h2>
      <p>{{ query.trim() ? '다른 단어로 검색해 보세요.' : '궁금한 점을 첫 질문으로 남겨보세요.' }}</p>
      <RouterLink v-if="!query.trim()" class="button-primary" :to="{ name: 'question-create' }">첫 질문 작성</RouterLink>
    </div>
  </section>
</template>
