<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { createApiClient } from '../api'

const router = useRouter()
const form = ref({ name: '', email: '', password: '' })
const submitting = ref(false)
const error = ref('')

async function submitSignup() {
  error.value = ''
  submitting.value = true
  try {
    await createApiClient().signup(form.value)
    await router.push({ name: 'login', query: { created: '1' } })
  } catch (requestError) { error.value = requestError.message || 'Your account could not be created.' }
  finally { submitting.value = false }
}
</script>

<template>
  <section class="auth-page" aria-labelledby="signup-title">
    <div class="auth-aside auth-aside--butter"><span class="auth-aside__mark" aria-hidden="true">⌂</span><p>Start with a space<br />that feels like home.</p><span class="auth-aside__caption">A new chapter can start here.</span></div>
    <div class="auth-card"><p class="section-label">GET STARTED</p><h1 id="signup-title">Create account</h1><p class="auth-copy">Create an account to keep exploring homes.</p>
      <form class="auth-form" @submit.prevent="submitSignup"><label class="field-label" for="signup-name">Name</label><input id="signup-name" v-model.trim="form.name" type="text" autocomplete="name" placeholder="Your name" required /><label class="field-label" for="signup-email">Email</label><input id="signup-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" required /><label class="field-label" for="signup-password">Password</label><input id="signup-password" v-model="form.password" type="password" autocomplete="new-password" minlength="1" placeholder="Create a password" required /><p v-if="error" class="form-error" role="alert">{{ error }}</p><button class="button-primary button-primary--wide" type="submit" :disabled="submitting">{{ submitting ? 'Creating…' : 'Create account' }}</button></form>
      <p class="auth-switch">Already have an account? <RouterLink :to="{ name: 'login' }">Sign in</RouterLink></p>
    </div>
  </section>
</template>
