<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { createApiClient } from '../api/api.js'

const route = useRoute()
const router = useRouter()
const question = ref(null)
const loading = ref(true)
const error = ref('')
const editingQuestion = ref(false)
const questionForm = ref({ title: '', contents: '' })
const replacementImage = ref(null)
const previewUrl = ref('')
const removeCurrentImage = ref(false)
const answerText = ref('')
const editingAnswer = ref(false)
const saving = ref(false)
const supportedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

async function loadQuestion() {
  loading.value = true
  error.value = ''
  try {
    question.value = await createApiClient().readQuestion(route.params.id)
    answerText.value = question.value.answer?.contents || ''
  } catch (requestError) {
    error.value = requestError.message || '질문을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function startQuestionEdit() {
  questionForm.value = { title: question.value.title, contents: question.value.contents }
  replacementImage.value = null
  removeCurrentImage.value = false
  clearPreview()
  editingQuestion.value = true
  error.value = ''
}

function selectReplacementImage(event) {
  const file = event.target.files?.[0] || null
  error.value = ''
  clearPreview()
  replacementImage.value = null
  if (!file) return
  if (!supportedImageTypes.includes(file.type)) {
    error.value = 'JPEG, PNG, GIF, WebP 이미지 파일을 선택해 주세요.'
    event.target.value = ''
    return
  }
  replacementImage.value = file
  removeCurrentImage.value = false
  previewUrl.value = URL.createObjectURL(file)
}

function clearQuestionImage() {
  clearPreview()
  replacementImage.value = null
  removeCurrentImage.value = true
  const input = document.querySelector('#question-edit-image')
  if (input) input.value = ''
}

async function saveQuestion() {
  error.value = ''
  saving.value = true
  try {
    const api = createApiClient()
    let imageUrl = removeCurrentImage.value ? null : question.value.image_url
    if (replacementImage.value) imageUrl = await api.uploadQuestionImage(replacementImage.value)
    question.value = await api.updateQuestion(question.value.id, {
      title: questionForm.value.title.trim(),
      contents: questionForm.value.contents.trim(),
      image_url: imageUrl,
    })
    editingQuestion.value = false
  } catch (requestError) {
    error.value = requestError.message || '질문을 수정하지 못했습니다.'
  } finally {
    saving.value = false
  }
}

async function deleteQuestion() {
  error.value = ''
  saving.value = true
  try {
    await createApiClient().deleteQuestion(question.value.id)
    await router.push({ name: 'question-list' })
  } catch (requestError) {
    error.value = requestError.message || '질문을 삭제하지 못했습니다.'
  } finally {
    saving.value = false
  }
}

function startAnswerEdit() {
  answerText.value = question.value.answer?.contents || ''
  editingAnswer.value = true
  error.value = ''
}

async function saveAnswer() {
  error.value = ''
  saving.value = true
  try {
    const api = createApiClient()
    const data = { contents: answerText.value.trim() }
    question.value = question.value.answer
      ? await api.updateQuestionAnswer(question.value.id, data)
      : await api.createQuestionAnswer(question.value.id, data)
    answerText.value = question.value.answer.contents
    editingAnswer.value = false
  } catch (requestError) {
    error.value = requestError.message || '답변을 저장하지 못했습니다.'
  } finally {
    saving.value = false
  }
}

async function deleteAnswer() {
  error.value = ''
  saving.value = true
  try {
    await createApiClient().deleteQuestionAnswer(question.value.id)
    question.value = { ...question.value, answer: null }
    answerText.value = ''
    editingAnswer.value = false
  } catch (requestError) {
    error.value = requestError.message || '답변을 삭제하지 못했습니다.'
  } finally {
    saving.value = false
  }
}

onMounted(loadQuestion)
onBeforeUnmount(clearPreview)
</script>

<template>
  <section class="question-detail-page" aria-labelledby="question-title">
    <div class="detail-toolbar">
      <RouterLink class="back-link" :to="{ name: 'question-list' }"><span aria-hidden="true">←</span> 질문 게시판</RouterLink>
      <RouterLink class="button-secondary" :to="{ name: 'question-create' }">새 질문 <span aria-hidden="true">↗</span></RouterLink>
    </div>

    <div v-if="loading" class="detail-loading" aria-busy="true" aria-label="질문을 불러오는 중">
      <div class="detail-loading__line"></div><div class="detail-loading__line detail-loading__line--title"></div><div class="detail-loading__block"></div>
    </div>
    <div v-else-if="error && !question" class="empty-panel empty-panel--error" role="alert">
      <h2>질문을 찾지 못했어요.</h2><p>{{ error }}</p>
      <RouterLink class="button-secondary" :to="{ name: 'question-list' }">질문 게시판으로 돌아가기</RouterLink>
    </div>

    <template v-else-if="question">
      <article class="question-detail">
        <div class="question-detail__meta">
          <span>질문 {{ String(question.id).padStart(3, '0') }}</span>
          <span class="question-status" :class="{ 'question-status--answered': question.answer }">{{ question.answer ? '답변 완료' : '답변 기다리는 중' }}</span>
        </div>
        <form v-if="editingQuestion" class="question-edit-form" @submit.prevent="saveQuestion">
          <label class="field-label" for="question-edit-title">제목</label>
          <input id="question-edit-title" v-model="questionForm.title" class="editor-title-input" maxlength="200" required />
          <label class="field-label" for="question-edit-contents">내용</label>
          <textarea id="question-edit-contents" v-model="questionForm.contents" class="editor-body-input" rows="8" required></textarea>
          <label class="field-label" for="question-edit-image">이미지 <span class="field-optional">선택 · 1장</span></label>
          <input id="question-edit-image" class="question-file-input" type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="selectReplacementImage" />
          <img v-if="previewUrl" class="question-detail__image" :src="previewUrl" alt="변경할 첨부 이미지 미리보기" />
          <img v-else-if="question.image_url && !removeCurrentImage" class="question-detail__image" :src="question.image_url" alt="질문 첨부 이미지" />
          <button v-if="(question.image_url && !removeCurrentImage) || previewUrl" class="text-button" type="button" @click="clearQuestionImage">이미지 제거</button>
          <div class="question-detail__actions">
            <button class="button-secondary" type="button" @click="editingQuestion = false; clearPreview()">취소</button>
            <button class="button-primary" type="submit" :disabled="saving">{{ saving ? '저장 중…' : '변경 저장' }}</button>
          </div>
        </form>
        <template v-else>
          <h1 id="question-title">{{ question.title }}</h1>
          <p class="question-detail__contents">{{ question.contents }}</p>
          <img v-if="question.image_url" class="question-detail__image" :src="question.image_url" :alt="`${question.title} 첨부 이미지`" />
          <div class="question-detail__actions">
            <button class="button-secondary" type="button" @click="startQuestionEdit">질문 수정</button>
            <button class="text-button" type="button" :disabled="saving" @click="deleteQuestion">질문 삭제</button>
          </div>
        </template>
      </article>

      <section class="answer-section" aria-labelledby="answer-heading">
        <div class="answer-section__heading">
          <div><p class="section-label">한 곳에 남기는 답변</p><h2 id="answer-heading">답변</h2></div>
          <span>{{ question.answer ? '1개' : '아직 없음' }}</span>
        </div>
        <article v-if="question.answer && !editingAnswer" class="answer-sheet">
          <p>{{ question.answer.contents }}</p>
          <div class="question-detail__actions">
            <button class="button-secondary" type="button" @click="startAnswerEdit">답변 수정</button>
            <button class="text-button" type="button" :disabled="saving" @click="deleteAnswer">답변 삭제</button>
          </div>
        </article>
        <form v-if="!question.answer || editingAnswer" class="answer-form" @submit.prevent="saveAnswer">
          <label class="visually-hidden" for="answer-contents">답변 내용</label>
          <textarea id="answer-contents" v-model="answerText" class="editor-body-input" rows="5" :placeholder="question.answer ? '답변을 수정해 주세요.' : '질문에 답변을 남겨주세요.'" required></textarea>
          <div class="question-detail__actions">
            <button v-if="question.answer" class="button-secondary" type="button" @click="editingAnswer = false">취소</button>
            <button class="button-primary" type="submit" :disabled="saving">{{ saving ? '저장 중…' : question.answer ? '답변 수정' : '답변 등록' }}</button>
          </div>
        </form>
      </section>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    </template>
  </section>
</template>
