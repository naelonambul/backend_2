<script setup>
import { computed, onMounted, ref } from 'vue'
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
    error.value = requestError.message || 'This home could not be loaded.'
    apiErrorStatus.value = requestError.status
  } finally {
    loading.value = false
  }
}

onMounted(loadProperty)
</script>

<template>
  <section class="property-detail-page">
    <div class="detail-toolbar"><RouterLink class="back-link" :to="{ name: 'property-list' }"><span aria-hidden="true">←</span> All homes</RouterLink></div>
    <div v-if="loading" class="detail-loading" role="status" aria-label="Loading home details"><div class="detail-loading__line"></div><div class="detail-loading__block"></div></div>
    <div v-else-if="error" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span><h2>{{ notFound ? 'Home not found' : "We couldn't load this home" }}</h2><p>{{ notFound ? 'This listing may have been removed or the link is incorrect.' : error }}</p>
      <button v-if="!notFound" class="button-secondary" type="button" @click="loadProperty">Try again</button>
      <RouterLink class="button-primary" :to="{ name: 'property-list' }">Browse all homes</RouterLink>
    </div>
    <article v-else-if="property" class="property-detail">
      <div class="property-detail__image">
        <img v-if="property.image_url" :src="property.image_url" :alt="property.title" />
        <div v-else class="property-placeholder property-placeholder--large" aria-label="No property image available"><span class="placeholder-sun"></span><span class="placeholder-home"><i></i></span></div>
        <span class="property-card__tag">FOR SALE</span>
      </div>
      <div class="property-detail__content">
        <div class="property-detail__intro"><div><p class="property-card__address">{{ property.address }}</p><h1>{{ property.title }}</h1></div><strong class="property-detail__price">{{ formatPrice(property.price_krw) }}</strong></div>
        <div class="property-detail__facts"><div><span>AREA</span><strong>{{ formatArea(property.area_m2) }}</strong></div><div><span>ROOMS</span><strong>{{ property.room_count }}</strong></div><div><span>LISTING</span><strong>#{{ property.idx }}</strong></div></div>
        <section class="property-description"><p class="section-label">ABOUT THIS HOME</p><p>{{ property.description }}</p></section>
        <RouterLink class="button-secondary" :to="{ name: 'property-list' }">← Back to all homes</RouterLink>
      </div>
    </article>
  </section>
</template>
