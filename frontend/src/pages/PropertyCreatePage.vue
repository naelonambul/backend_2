<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api'
import { getCurrentUserOrNull } from '../auth/session'
import { getSellerAccessState, validatePropertyForm } from '../lib/property-view'

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
    accessError.value = requestError.message || 'Your account access could not be checked.'
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
    error.value = requestError.message || 'The listing could not be published.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="property-create-page">
    <RouterLink class="back-link" :to="{ name: 'property-list' }"><span aria-hidden="true">←</span> All homes</RouterLink>
    <div class="editor-heading"><p class="section-label">SELLER STUDIO</p><h1>Share a new home</h1><p>Give buyers the details they need to picture life here.</p></div>

    <div v-if="accessState === 'loading'" class="empty-panel" role="status"><h2>Checking seller access…</h2><p>One moment while we check your account.</p></div>
    <div v-else-if="accessState === 'error'" class="empty-panel empty-panel--error" role="alert"><h2>We couldn't verify your account</h2><p>{{ accessError }}</p><RouterLink class="button-primary" :to="{ name: 'property-list' }">Back to homes</RouterLink></div>
    <div v-else-if="accessState === 'buyer'" class="empty-panel"><span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>Seller access only</h2><p>You can browse every home in the collection, but only the configured seller can publish listings.</p><RouterLink class="button-primary" :to="{ name: 'property-list' }">Browse homes</RouterLink></div>
    <div v-else-if="accessState === 'guest'" class="empty-panel"><span class="empty-panel__symbol" aria-hidden="true">⌂</span><h2>Sign in to continue</h2><p>Sign in with the seller account to publish a property.</p><RouterLink class="button-primary" :to="{ name: 'login', query: { redirect: '/properties/new' } }">Sign in</RouterLink><RouterLink class="back-link" :to="{ name: 'property-list' }">Return to listings</RouterLink></div>
    <form v-else class="property-form" @submit.prevent="submitListing" novalidate>
      <div class="property-form__section"><p class="section-label">THE HOME</p>
        <label class="field-label" for="property-title">Listing title</label><input id="property-title" v-model="form.title" class="editor-title-input" maxlength="200" required placeholder="A sunlit home near the park" /><p v-if="fieldErrors.title" class="form-error">{{ fieldErrors.title }}</p>
        <label class="field-label" for="property-address">Address</label><input id="property-address" v-model="form.address" class="editor-title-input" maxlength="300" required placeholder="Neighborhood, city" /><p v-if="fieldErrors.address" class="form-error">{{ fieldErrors.address }}</p>
        <label class="field-label" for="property-description">Description</label><textarea id="property-description" v-model="form.description" class="editor-body-input" maxlength="5000" required placeholder="Describe the spaces, the light, and what makes this home special."></textarea><p v-if="fieldErrors.description" class="form-error">{{ fieldErrors.description }}</p>
      </div>
      <div class="property-form__section"><p class="section-label">HOME DETAILS</p><div class="property-form__numbers">
        <div><label class="field-label" for="property-price">Price (KRW)</label><input id="property-price" v-model="form.price_krw" class="editor-title-input" type="number" min="0" step="1" required placeholder="500000000" /><p v-if="fieldErrors.price_krw" class="form-error">{{ fieldErrors.price_krw }}</p></div>
        <div><label class="field-label" for="property-area">Area (m²)</label><input id="property-area" v-model="form.area_m2" class="editor-title-input" type="number" min="0.01" step="any" required placeholder="84.5" /><p v-if="fieldErrors.area_m2" class="form-error">{{ fieldErrors.area_m2 }}</p></div>
        <div><label class="field-label" for="property-rooms">Rooms</label><input id="property-rooms" v-model="form.room_count" class="editor-title-input" type="number" min="0" step="1" required placeholder="3" /><p v-if="fieldErrors.room_count" class="form-error">{{ fieldErrors.room_count }}</p></div>
      </div>
        <label class="field-label" for="property-image">Image URL <span class="field-optional">OPTIONAL</span></label><input id="property-image" v-model="form.image_url" class="editor-title-input" type="url" placeholder="https://example.com/home.jpg" /><p v-if="fieldErrors.image_url" class="form-error">{{ fieldErrors.image_url }}</p>
      </div>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <div class="property-form__footer"><p>Listing details are visible to all visitors.</p><div class="editor-actions"><RouterLink class="button-secondary" :to="{ name: 'property-list' }">Cancel</RouterLink><button class="button-primary" type="submit" :disabled="submitting">{{ submitting ? 'Publishing…' : 'Publish listing' }} <span aria-hidden="true">↗</span></button></div></div>
    </form>
  </section>
</template>
