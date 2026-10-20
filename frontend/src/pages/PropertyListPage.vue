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
    error.value = requestError.message || 'Listings could not be loaded.'
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
        <p class="section-label">A PLACE TO CALL YOUR OWN</p>
        <h1 id="market-title">Find a home<br /><span>that feels like you.</span></h1>
        <p>Thoughtfully selected homes for the next chapter of your life.</p>
        <RouterLink class="button-primary" :to="{ name: 'property-list' }">Explore homes <span aria-hidden="true">↘</span></RouterLink>
      </div>
      <div class="market-hero__art" aria-hidden="true">
        <div class="hero-sun"></div><div class="hero-house"><div class="hero-roof"></div><div class="hero-wall"><i></i><i></i><b></b></div></div>
        <span class="hero-caption">ROOM TO GROW · SPACE TO BREATHE</span>
      </div>
    </div>

    <div class="listing-heading">
      <div><p class="section-label">THE COLLECTION</p><h2>Homes for your next chapter</h2><p>Browse every available listing, open and ready to explore.</p></div>
      <span class="listing-count"><strong>{{ properties.length }}</strong> homes</span>
    </div>

    <div v-if="state === 'loading'" class="property-grid" aria-label="Loading listings" aria-busy="true">
      <div v-for="item in 3" :key="item" class="property-skeleton"><div></div><i></i><i></i></div>
    </div>
    <div v-else-if="state === 'error'" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span><h2>We couldn't load the listings</h2><p>{{ error }}</p>
      <button class="button-secondary" type="button" @click="loadProperties">Try again</button>
    </div>
    <div v-else-if="state === 'empty'" class="empty-panel">
      <span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>No homes listed yet</h2><p>Check back soon to see new homes in the collection.</p>
    </div>
    <div v-else class="property-grid">
      <RouterLink v-for="property in properties" :key="property.idx" class="property-card" :to="{ name: 'property-detail', params: { idx: property.idx } }">
        <div class="property-card__image">
          <img v-if="property.image_url" :src="property.image_url" :alt="property.title" loading="lazy" />
          <div v-else class="property-placeholder" aria-label="No property image available"><span class="placeholder-sun"></span><span class="placeholder-home"><i></i></span></div>
          <span class="property-card__tag">FOR SALE</span>
        </div>
        <div class="property-card__body">
          <p class="property-card__address">{{ property.address }}</p><h3>{{ property.title }}</h3>
          <p class="property-card__facts">{{ formatArea(property.area_m2) }} <span>·</span> {{ property.room_count }} rooms</p>
          <div class="property-card__bottom"><strong>{{ formatPrice(property.price_krw) }}</strong><span>View home <b aria-hidden="true">↗</b></span></div>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
