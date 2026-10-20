<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api/api.js'
import { getCurrentUserOrNull } from '../stores/auth/session.js'
import { getSellerAccessState, validatePropertyForm } from '../stores/property/view.js'

const router = useRouter()
const api = createApiClient()
const form = reactive({ title: '', address: '', price_krw: '', area_m2: '', room_count: '', description: '', image_url: '' })
const currentUser = ref(null)
const loading = ref(true)
const accessError = ref('')
const submitting = ref(false)
const error = ref('')
const fieldErrors = ref({})
const accessState = computed(() => getSellerAccessState({ loading: loading.value, error: accessError.value, role: currentUser.value?.role ?? null }))

onMounted(async () => {
  try {
    currentUser.value = await getCurrentUserOrNull(api)
  } catch (requestError) {
    accessError.value = requestError.message || '계정 권한을 확인하지 못했습니다.'
  } finally {
    loading.value = false
  }
})

async function submitListing() {
  error.value = ''
  const validation = validatePropertyForm(form)
  fieldErrors.value = validation.errors
  if (!validation.valid) return

  submitting.value = true
  try {
    const created = await api.registerProperty(validation.data)
    await router.push({ name: 'property-detail', params: { idx: created.idx } })
  } catch (requestError) {
    error.value = requestError.message || '매물을 등록하지 못했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="property-create-page">
    <RouterLink class="back-link" :to="{ name: 'property-list' }"><span aria-hidden="true">←</span> 매물 목록</RouterLink>
    <div class="editor-heading"><p class="section-label">판매자 공간</p><h1>새 매물 등록</h1><p>집의 특징과 정보를 자세히 소개해 주세요.</p></div>

    <div v-if="accessState === 'loading'" class="empty-panel" role="status"><h2>판매자 권한을 확인하고 있어요</h2><p>잠시만 기다려 주세요.</p></div>
    <div v-else-if="accessState === 'error'" class="empty-panel empty-panel--error" role="alert"><h2>계정 권한을 확인하지 못했어요</h2><p>{{ accessError }}</p><RouterLink class="button-primary" :to="{ name: 'property-list' }">매물 목록으로</RouterLink></div>
    <div v-else-if="accessState === 'buyer'" class="empty-panel"><span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>판매자 전용 페이지입니다</h2><p>매물은 누구나 둘러볼 수 있지만, 등록은 지정된 판매자 계정만 할 수 있어요.</p><RouterLink class="button-primary" :to="{ name: 'property-list' }">매물 둘러보기</RouterLink></div>
    <div v-else-if="accessState === 'guest'" class="empty-panel"><span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>로그인이 필요해요</h2><p>판매자 계정으로 로그인하면 매물을 등록할 수 있습니다.</p><RouterLink class="button-primary" :to="{ name: 'login', query: { redirect: '/properties/new' } }">로그인</RouterLink><RouterLink class="back-link" :to="{ name: 'property-list' }">매물 목록으로 돌아가기</RouterLink></div>
    <form v-else class="property-form" @submit.prevent="submitListing" novalidate>
      <div class="property-form__section"><p class="section-label">매물 정보</p>
        <label class="field-label" for="property-title">매물 제목</label><input id="property-title" v-model="form.title" class="editor-title-input" maxlength="200" required placeholder="공원 가까운 햇살 가득한 집" /><p v-if="fieldErrors.title" class="form-error">{{ fieldErrors.title }}</p>
        <label class="field-label" for="property-address">주소</label><input id="property-address" v-model="form.address" class="editor-title-input" maxlength="300" required placeholder="시·구·동 및 상세 주소" /><p v-if="fieldErrors.address" class="form-error">{{ fieldErrors.address }}</p>
        <label class="field-label" for="property-description">매물 설명</label><textarea id="property-description" v-model="form.description" class="editor-body-input" maxlength="5000" required placeholder="집의 구조와 채광, 주변 환경 등 특징을 소개해 주세요."></textarea><p v-if="fieldErrors.description" class="form-error">{{ fieldErrors.description }}</p>
      </div>
      <div class="property-form__section"><p class="section-label">집 상세 정보</p><div class="property-form__numbers">
        <div><label class="field-label" for="property-price">매매가 (원)</label><input id="property-price" v-model="form.price_krw" class="editor-title-input" type="number" min="0" step="1" required placeholder="500000000" /><p v-if="fieldErrors.price_krw" class="form-error">{{ fieldErrors.price_krw }}</p></div>
        <div><label class="field-label" for="property-area">전용 면적 (㎡)</label><input id="property-area" v-model="form.area_m2" class="editor-title-input" type="number" min="0.01" step="any" required placeholder="84.5" /><p v-if="fieldErrors.area_m2" class="form-error">{{ fieldErrors.area_m2 }}</p></div>
        <div><label class="field-label" for="property-rooms">방 개수</label><input id="property-rooms" v-model="form.room_count" class="editor-title-input" type="number" min="0" step="1" required placeholder="3" /><p v-if="fieldErrors.room_count" class="form-error">{{ fieldErrors.room_count }}</p></div>
      </div>
        <label class="field-label" for="property-image">사진 주소 <span class="field-optional">선택 입력</span></label><input id="property-image" v-model="form.image_url" class="editor-title-input" type="url" placeholder="https://example.com/home.jpg" /><p v-if="fieldErrors.image_url" class="form-error">{{ fieldErrors.image_url }}</p>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <div class="property-form__footer"><p>등록한 매물 정보는 모든 방문자에게 공개됩니다.</p><div class="editor-actions"><RouterLink class="button-secondary" :to="{ name: 'property-list' }">취소</RouterLink><button class="button-primary" type="submit" :disabled="submitting">{{ submitting ? '등록 중…' : '매물 등록하기' }} <span aria-hidden="true">↗</span></button></div></div>
    </form>
  </section>
</template>
