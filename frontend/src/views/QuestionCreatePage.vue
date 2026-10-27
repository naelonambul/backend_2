<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api/api.js'

const router = useRouter()
const form = ref({ title: '', contents: '' })
const selectedImage = ref(null)
const previewUrl = ref('')
const submitting = ref(false)
const error = ref('')
const supportedImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

function selectImage(event) {
  const file = event.target.files?.[0] || null
  error.value = ''
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  selectedImage.value = null
  if (!file) return
  if (!supportedImageTypes.includes(file.type)) {
    error.value = 'JPEG, PNG, GIF, WebP 이미지 파일을 선택해 주세요.'
    event.target.value = ''
    return
  }
  selectedImage.value = file
  previewUrl.value = URL.createObjectURL(file)
}

function removeImage() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  selectedImage.value = null
  const input = document.querySelector('#question-image')
  if (input) input.value = ''
}

async function submitQuestion() {
  error.value = ''
  submitting.value = true
  try {
    const api = createApiClient()
    const imageUrl = selectedImage.value ? await api.uploadQuestionImage(selectedImage.value) : null
    const question = await api.createQuestion({
      title: form.value.title.trim(),
      contents: form.value.contents.trim(),
      image_url: imageUrl,
    })
    await router.push({ name: 'question-detail', params: { id: question.id } })
  } catch (requestError) {
    error.value = requestError.message || '질문을 저장하지 못했습니다.'
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <section class="question-editor-page" aria-labelledby="question-editor-title">
    <RouterLink class="back-link" :to="{ name: 'question-list' }"><span aria-hidden="true">←</span> 질문 게시판</RouterLink>
    <div class="editor-heading">
      <p class="section-label">새 질문</p>
      <h1 id="question-editor-title">궁금한 점을 들려주세요.</h1>
      <p>필요하면 사진 한 장을 함께 올릴 수 있어요.</p>
    </div>
    <form class="question-form" @submit.prevent="submitQuestion">
      <label class="field-label" for="question-title">제목</label>
      <input id="question-title" v-model="form.title" class="editor-title-input" name="title" maxlength="200" placeholder="질문을 한 문장으로 적어주세요" autocomplete="off" required />

      <label class="field-label" for="question-contents">내용</label>
      <textarea id="question-contents" v-model="form.contents" class="editor-body-input" name="contents" rows="9" placeholder="궁금한 점을 자세히 적어주세요" required></textarea>

      <div class="question-image-field">
        <label class="field-label" for="question-image">이미지 <span class="field-optional">선택 · 1장</span></label>
        <input id="question-image" class="question-file-input" type="file" accept="image/jpeg,image/png,image/gif,image/webp" aria-describedby="question-image-help" @change="selectImage" />
        <p id="question-image-help" class="question-image-help">JPEG, PNG, GIF, WebP 이미지 파일 1개를 선택할 수 있어요.</p>
        <div v-if="previewUrl" class="question-image-preview">
          <img :src="previewUrl" alt="질문에 첨부할 이미지 미리보기" />
          <button class="text-button" type="button" @click="removeImage">이미지 제거</button>
        </div>
      </div>

      <div class="question-form__footer">
        <span>{{ form.contents.length }}자</span>
        <div class="editor-actions">
          <RouterLink class="button-secondary" :to="{ name: 'question-list' }">취소</RouterLink>
          <button class="button-primary" type="submit" :disabled="submitting">{{ submitting ? '등록 중…' : '질문 등록' }}</button>
        </div>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    </form>
  </section>
</template>
