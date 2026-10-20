<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createApiClient } from '../api'
import { formatArea, formatPrice, getPropertyListState } from '../lib/property-view'

const api = createApiClient()
const properties = ref([])
const loading = ref(true)
const error = ref('')
const state = computed(() => getPropertyListState({ loading: loading.value, error: error.value, properties: properties.value }))

async function loadProperties() {
  loading.value = true
  error.value = ''
  try {
    properties.value = await api.listProperties()
  } catch (requestError) {
    error.value = requestError.message || '매물 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(loadProperties)
</script>

<template>
  <section class="market-page" aria-labelledby="market-title">
    <div class="market-hero">
      <div class="market-hero__copy">
        <p class="section-label">나만의 공간을 찾아보세요</p>
        <h1 id="market-title">나에게 꼭 맞는<br /><span>집을 만나보세요.</span></h1>
        <p>새로운 시작을 함께할 집을 둘러보고 다음 장면을 그려보세요.</p>
        <RouterLink class="button-primary" :to="{ name: 'property-list' }">매물 둘러보기 <span aria-hidden="true">↘</span></RouterLink>
      </div>
      <div class="market-hero__art" aria-hidden="true">
        <div class="hero-sun"></div><div class="hero-house"><div class="hero-roof"></div><div class="hero-wall"><i></i><i></i><b></b></div></div>
        <span class="hero-caption">넉넉한 공간 · 편안한 일상</span>
      </div>
    </div>

    <div class="listing-heading">
      <div><p class="section-label">하벤의 매물</p><h2>새로운 일상을 위한 집</h2><p>지금 둘러볼 수 있는 매물을 한곳에서 확인하세요.</p></div>
      <span class="listing-count"><strong>{{ properties.length }}</strong>개 매물</span>
    </div>

    <div v-if="state === 'loading'" class="property-grid" aria-label="매물 목록 불러오는 중" aria-busy="true">
      <div v-for="item in 3" :key="item" class="property-skeleton"><div></div><i></i><i></i></div>
    </div>
    <div v-else-if="state === 'error'" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span><h2>매물 목록을 불러오지 못했어요</h2><p>{{ error }}</p>
      <button class="button-secondary" type="button" @click="loadProperties">다시 시도</button>
    </div>
    <div v-else-if="state === 'empty'" class="empty-panel">
      <span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>등록된 매물이 아직 없어요</h2><p>새로운 매물이 등록되면 이곳에서 확인할 수 있어요.</p>
    </div>
    <div v-else class="property-grid">
      <RouterLink v-for="property in properties" :key="property.idx" class="property-card" :to="{ name: 'property-detail', params: { idx: property.idx } }">
        <div class="property-card__image">
          <img v-if="property.image_url" :src="property.image_url" :alt="property.title" loading="lazy" />
          <div v-else class="property-placeholder" aria-label="매물 사진 없음"><span class="placeholder-sun"></span><span class="placeholder-home"><i></i></span></div>
          <span class="property-card__tag">매매</span>
        </div>
        <div class="property-card__body">
          <p class="property-card__address">{{ property.address }}</p><h3>{{ property.title }}</h3>
          <p class="property-card__facts">{{ formatArea(property.area_m2) }} <span>·</span> 방 {{ property.room_count }}개</p>
          <div class="property-card__bottom"><strong>{{ formatPrice(property.price_krw) }}</strong><span>매물 보기 <b aria-hidden="true">↗</b></span></div>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
