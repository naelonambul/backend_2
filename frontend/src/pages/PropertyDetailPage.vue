<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import { formatArea, formatPrice } from '../lib/property-view'

const route = useRoute()
const api = createApiClient()
const property = ref(null)
const loading = ref(true)
const error = ref('')
const notFound = computed(() => error.value && apiErrorStatus.value === 404)
const apiErrorStatus = ref(null)

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
        <div class="property-detail__intro"><div><p class="property-card__address">{{ property.address }}</p><h1>{{ property.title }}</h1></div><strong class="property-detail__price">{{ formatPrice(property.price_krw) }}</strong></div>
        <div class="property-detail__facts"><div><span>전용 면적</span><strong>{{ formatArea(property.area_m2) }}</strong></div><div><span>방 개수</span><strong>{{ property.room_count }}개</strong></div><div><span>매물 번호</span><strong>#{{ property.idx }}</strong></div></div>
        <section class="property-description"><p class="section-label">집 소개</p><p>{{ property.description }}</p></section>
        <RouterLink class="button-secondary" :to="{ name: 'property-list' }">← 매물 목록으로</RouterLink>
      </div>
    </article>
  </section>
</template>
