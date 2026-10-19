<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const route = useRoute()
const form = ref({ email: typeof route.query.email === 'string' ? route.query.email : '', password: '' })
const loading = ref(false)
const message = ref('')
const error = ref('')
const loggedInEmail = ref('')
const isLoggedIn = computed(() => Boolean(loggedInEmail.value))

async function submitLogin() {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const user = await createApiClient().login({ ...form.value })
    loggedInEmail.value = user.email
    message.value = '로그인했습니다. 인증 쿠키가 브라우저에 저장되었습니다.'
    form.value.password = ''
  } catch (requestError) {
    error.value = requestError.message || '로그인에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="page-heading">
      <span class="eyebrow"><i></i> WELCOME BACK</span>
      <h1>다시 반가워요.<br /><em>기록을 이어가세요.</em></h1>
      <p>가입한 이메일과 비밀번호로 로그인할 수 있어요.</p>
    </div>

    <PageSkeleton v-if="loading" variant="form" compact />
    <article v-else class="form-card auth-card">
      <div class="form-card-top"><div><span class="section-kicker">MEMBER LOGIN</span><h2>로그인</h2></div><span class="route-index">02 / 05</span></div>
      <form class="api-form" @submit.prevent="submitLogin">
        <label>이메일<input v-model.trim="form.email" name="email" type="email" autocomplete="email" placeholder="hello@example.com" required /></label>
        <label>비밀번호<input v-model="form.password" name="password" type="password" autocomplete="current-password" placeholder="비밀번호를 입력하세요" required /></label>
        <div class="auth-note"><span class="lock-mark">⌑</span><span>로그인하면 서버가 발급한 <code>EN_AT</code> 인증 쿠키를 사용합니다.</span></div>
        <button class="primary-button" type="submit">로그인하기 <span>↗</span></button>
      </form>
      <p v-if="message" class="form-message success" role="status">{{ message }} <strong>{{ loggedInEmail }}</strong></p>
      <p v-if="error" class="form-message error" role="alert">{{ error }}</p>
      <p class="form-footnote">아직 계정이 없나요? <RouterLink :to="{ name: 'signup' }">회원가입</RouterLink></p>
      <span v-if="isLoggedIn" class="login-state">로그인 완료</span>
    </article>
  </section>
</template>
