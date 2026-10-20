<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import { beginKakaoLogin } from '../auth/kakao'
import { getCurrentUserOrNull } from '../auth/session'

const route = useRoute()
const api = createApiClient()
const form = ref({ email: '', password: '' })
const currentUser = ref(null)
const sessionLoading = ref(true)
const sessionError = ref('')
const submitting = ref(false)
const kakaoSubmitting = ref(false)
const logoutSubmitting = ref(false)
const error = ref('')
const justCreated = computed(() => route.query.created === '1')

onMounted(async () => {
  try { currentUser.value = await getCurrentUserOrNull(api) }
  catch (requestError) { sessionError.value = requestError.message || 'Your sign-in status could not be checked.' }
  finally { sessionLoading.value = false }
})

async function submitLogin() {
  error.value = ''
  submitting.value = true
  try { await api.login(form.value); currentUser.value = await api.getCurrentUser() }
  catch (requestError) { error.value = requestError.message || 'Sign-in failed.' }
  finally { submitting.value = false }
}

async function submitLogout() {
  sessionError.value = ''
  logoutSubmitting.value = true
  try { await api.logout(); currentUser.value = null }
  catch (requestError) { sessionError.value = requestError.message || 'Sign-out failed.' }
  finally { logoutSubmitting.value = false }
}

async function submitKakaoLogin() {
  error.value = ''
  kakaoSubmitting.value = true
  try {
    const frontendOrigin = typeof __FRONTEND_ORIGIN__ !== 'undefined' ? __FRONTEND_ORIGIN__ : window.location.origin
    const redirectUri = import.meta.env.VITE_KAKAO_REDIRECT_URI || `${frontendOrigin}/auth/kakao/callback`
    await beginKakaoLogin({ sdk: window.Kakao, javascriptKey: import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY, redirectUri, api })
  } catch (requestError) { error.value = requestError.message || 'Kakao sign-in could not be started.' }
  finally { kakaoSubmitting.value = false }
}
</script>

<template>
  <section class="auth-page" aria-labelledby="login-title">
    <div class="auth-aside auth-aside--mint"><span class="auth-aside__mark" aria-hidden="true">⌂</span><p>Find a place<br />to call your own.</p><span class="auth-aside__caption">Thoughtful homes for your next chapter.</span></div>
    <div class="auth-card">
      <template v-if="sessionLoading"><p class="section-label">YOUR ACCOUNT</p><h1 id="login-title">One moment</h1><p class="auth-copy" role="status">Checking your sign-in status…</p></template>
      <template v-else-if="currentUser">
        <p class="section-label">WELCOME BACK</p><h1 id="login-title">You're signed in</h1><p class="auth-copy">Account details for {{ currentUser.name }}.</p>
        <dl class="account-details"><div class="account-details__row"><dt>Name</dt><dd>{{ currentUser.name }}</dd></div><div class="account-details__row"><dt>Email</dt><dd>{{ currentUser.email || 'Not provided' }}</dd></div><div class="account-details__row"><dt>Sign-in method</dt><dd>{{ currentUser.provider === 'kakao' ? 'Kakao' : 'Email' }}</dd></div></dl>
        <p v-if="sessionError" class="form-error" role="alert">{{ sessionError }}</p><div class="account-actions"><RouterLink class="button-primary button-primary--wide" :to="{ name: 'property-list' }">Browse homes</RouterLink><button class="button-secondary" type="button" :disabled="logoutSubmitting" @click="submitLogout">{{ logoutSubmitting ? 'Signing out…' : 'Sign out' }}</button></div>
      </template>
      <template v-else>
        <p class="section-label">WELCOME TO HAVEN</p><h1 id="login-title">Sign in</h1><p class="auth-copy">Sign in to continue exploring thoughtful homes.</p>
        <p v-if="justCreated" class="form-success" role="status">Your account is ready. Sign in to continue.</p><p v-if="sessionError" class="form-error" role="alert">{{ sessionError }}</p>
        <form class="auth-form" @submit.prevent="submitLogin"><label class="field-label" for="login-email">Email</label><input id="login-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" required /><label class="field-label" for="login-password">Password</label><input id="login-password" v-model="form.password" type="password" autocomplete="current-password" placeholder="Enter your password" required /><p v-if="error" class="form-error" role="alert">{{ error }}</p><button class="button-primary button-primary--wide" type="submit" :disabled="submitting">{{ submitting ? 'Signing in…' : 'Sign in' }}</button></form>
        <div class="auth-divider" aria-hidden="true"><span>or</span></div><button class="button-kakao" type="button" :disabled="kakaoSubmitting" @click="submitKakaoLogin"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5c-5.25 0-9.5 3.37-9.5 7.53 0 2.64 1.84 4.96 4.62 6.31l-.95 3.48c-.08.29.24.52.5.36l4.05-2.65c.42.06.84.09 1.28.09 5.25 0 9.5-3.37 9.5-7.53S17.25 3.5 12 3.5Z" /></svg>{{ kakaoSubmitting ? 'Connecting to Kakao…' : 'Continue with Kakao' }}</button>
        <p class="auth-switch">New to Haven? <RouterLink :to="{ name: 'signup' }">Create an account</RouterLink></p>
      </template>
    </div>
  </section>
</template>
