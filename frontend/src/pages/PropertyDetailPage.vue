<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import { getCurrentUserOrNull } from '../auth/session'
import { formatArea, formatPrice } from '../lib/property-view'
import PortOne from '../lib/portone'
import { canRetryPropertyPurchase, canStartPropertyPurchase, confirmPropertyPurchaseReturn, startPropertyPurchase } from '../lib/property-purchase'

const route = useRoute()
const api = createApiClient()
const property = ref(null)
const loading = ref(true)
const error = ref('')
const currentUser = ref(null)
const sessionLoading = ref(true)
const sessionError = ref('')
const checkoutLoading = ref(false)
const checkoutState = ref('')
const checkoutError = ref('')
const notFound = computed(() => error.value && apiErrorStatus.value === 404)
const apiErrorStatus = ref(null)
const canPurchase = computed(() => canStartPropertyPurchase({ role: currentUser.value?.role, availability: property.value?.availability }))

async function loadProperty() {
  loading.value = true
  error.value = ''
  apiErrorStatus.value = null
  try {
    property.value = await api.readProperty(route.params.idx)
  } catch (requestError) {
    error.value = requestError.message || '매물 정보를 불러오지 못했습니다.'
    apiErrorStatus.value = requestError.status
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    currentUser.value = await getCurrentUserOrNull(api)
  } catch (requestError) {
    sessionError.value = requestError.message || '로그인 상태를 확인하지 못했습니다.'
  } finally {
    sessionLoading.value = false
  }
})

async function startCheckout() {
  if (!property.value || !canPurchase.value || checkoutLoading.value) return
  checkoutError.value = ''
  checkoutState.value = ''
  checkoutLoading.value = true
  try {
    const result = await startPropertyPurchase({
      propertyIdx: property.value.idx,
      api,
      portone: PortOne,
      storeId: import.meta.env.VITE_PORTONE_STORE_ID,
      channelKey: import.meta.env.VITE_PORTONE_CHANNEL_KEY,
      redirectUrl: `${window.location.origin}/properties/purchase/return`,
      sessionStorage: window.sessionStorage,
    })
    checkoutState.value = result.state
    if (result.state === 'success' || result.state === 'cancelled') await loadProperty()
  } catch (requestError) {
    checkoutError.value = requestError.message || '결제를 시작하지 못했습니다.'
  } finally {
    checkoutLoading.value = false
  }
}

async function retryPurchaseConfirmation() {
  if (checkoutLoading.value) return
  checkoutError.value = ''
  checkoutLoading.value = true
  try {
    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage: window.sessionStorage })
    checkoutState.value = result.state
    if (result.state === 'success') await loadProperty()
    if (result.state === 'terminal-error') checkoutError.value = result.error?.message || '결제 결과를 확인하지 못했습니다.'
  } finally {
    checkoutLoading.value = false
  }
}

watch(() => route.params.idx, () => loadProperty(), { immediate: true })
</script>

<template>
  <section class="property-detail-page">
    <div class="detail-toolbar"><RouterLink class="back-link" :to="{ name: 'property-list' }"><span aria-hidden="true">←</span> 매물 목록</RouterLink></div>
    <div v-if="loading" class="detail-loading" role="status" aria-label="매물 정보 불러오는 중"><div class="detail-loading__line"></div><div class="detail-loading__block"></div></div>
    <div v-else-if="error" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span><h2>{{ notFound ? '매물을 찾을 수 없습니다' : '매물 정보를 불러오지 못했어요' }}</h2><p>{{ notFound ? '매물이 삭제되었거나 주소가 올바르지 않을 수 있습니다.' : error }}</p>
      <button v-if="!notFound" class="button-secondary" type="button" @click="loadProperty">다시 시도</button>
      <RouterLink class="button-primary" :to="{ name: 'property-list' }">매물 목록 보기</RouterLink>
    </div>
    <article v-else-if="property" class="property-detail">
      <div class="property-detail__image">
        <img v-if="property.image_url" :src="property.image_url" :alt="property.title" />
        <div v-else class="property-placeholder property-placeholder--large" aria-label="매물 사진 없음"><span class="placeholder-sun"></span><span class="placeholder-home"><i></i></span></div>
        <span class="property-card__tag">매매</span>
      </div>
      <div class="property-detail__content">
        <div class="property-detail__intro"><div><p class="property-card__address">{{ property.address }}</p><h1>{{ property.title }}</h1></div><strong v-if="canPurchase" class="property-detail__price">{{ formatPrice(property.price_krw) }}</strong></div>
        <div class="property-detail__facts"><div><span>전용 면적</span><strong>{{ formatArea(property.area_m2) }}</strong></div><div><span>방 개수</span><strong>{{ property.room_count }}개</strong></div><div><span>매물 번호</span><strong>#{{ property.idx }}</strong></div></div>
        <section class="property-description"><p class="section-label">집 소개</p><p>{{ property.description }}</p></section>
        <section v-if="sessionLoading" class="purchase-panel" role="status">로그인 상태를 확인하고 있어요.</section>
        <section v-else-if="sessionError" class="purchase-panel purchase-panel--error" role="alert">{{ sessionError }}</section>
        <section v-else-if="currentUser?.role === 'buyer' && property.availability === 'available'" class="purchase-panel">
          <div><p class="section-label">구매 안내</p><strong class="purchase-panel__price">{{ formatPrice(property.price_krw) }}</strong><p>안전한 카드 결제를 위해 주문 정보를 서버에서 확인합니다.</p></div>
          <button v-if="!canRetryPropertyPurchase(checkoutState)" class="button-primary" type="button" :disabled="checkoutLoading" @click="startCheckout">{{ checkoutLoading ? '결제창 여는 중…' : '카드로 구매하기' }} <span aria-hidden="true">↗</span></button>
        </section>
        <section v-else-if="currentUser?.role === 'buyer'" class="purchase-panel"><p class="section-label">매물 상태</p><strong>{{ property.availability === 'sold' ? '판매 완료된 매물입니다.' : '현재 다른 구매자가 결제를 진행 중입니다.' }}</strong></section>
        <button v-if="currentUser?.role === 'buyer' && canRetryPropertyPurchase(checkoutState)" class="button-primary purchase-login" type="button" :disabled="checkoutLoading" @click="retryPurchaseConfirmation">{{ checkoutLoading ? '결과 확인 중…' : checkoutState === 'refund_pending' ? '환불 상태 다시 확인' : '결제 결과 다시 확인' }}</button>
        <p v-if="currentUser?.role === 'seller'" class="purchase-note">판매자 계정으로 로그인되어 있어 구매할 수 없습니다.</p>
        <RouterLink v-else-if="!currentUser && !sessionLoading && !sessionError" class="button-primary purchase-login" :to="{ name: 'login', query: { redirect: route.fullPath } }">로그인하고 구매하기</RouterLink>
        <p v-if="checkoutError" class="form-error" role="alert">{{ checkoutError }}</p>
        <p v-else-if="checkoutState === 'cancelled'" class="purchase-note" role="status">결제가 취소되었습니다. 원하시면 다시 시도해 주세요.</p>
        <p v-else-if="checkoutState === 'pending' || checkoutState === 'retryable-error'" class="purchase-note" role="status">결제 결과를 확인하고 있습니다. 같은 주문의 확인 버튼을 눌러 다시 확인해 주세요.</p>
        <p v-else-if="checkoutState === 'refund_pending'" class="purchase-note" role="alert">결제는 승인되었지만 취소 확인이 필요합니다. 환불 상태를 다시 확인해 주세요.</p>
        <p v-else-if="checkoutState === 'failed' || checkoutState === 'terminal-error'" class="purchase-note" role="alert">결제가 완료되지 않았습니다. 매물 상태를 다시 확인해 주세요.</p>
        <RouterLink class="button-secondary" :to="{ name: 'property-list' }">← 매물 목록으로</RouterLink>
      </div>
    </article>
  </section>
</template>

<style scoped>
.purchase-panel { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin: 6px 0 27px; padding: 23px 25px; border: 1px solid #dce8e1; border-radius: 15px; background: #f4f8f5; }
.purchase-panel .section-label { margin: 0 0 8px; }
.purchase-panel__price { display: block; color: #345f4e; font-size: 23px; }
.purchase-panel > div > p:last-child { margin: 8px 0 0; color: #78877f; font-size: 12px; }
.purchase-panel > .button-primary { flex: 0 0 auto; }
.purchase-panel--error { color: #a64e3d; }
.purchase-note { margin: 0 0 25px; color: #77867e; font-size: 13px; line-height: 1.6; }
.purchase-login { display: inline-flex; margin: 4px 0 25px; text-decoration: none; }

@media (max-width: 640px) {
  .purchase-panel { align-items: stretch; flex-direction: column; padding: 19px; }
}
</style>
