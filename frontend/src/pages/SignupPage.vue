<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createApiClient } from '../api'
import PageSkeleton from '../components/PageSkeleton.vue'

const form = ref({ name: '', email: '', password: '' })
const loading = ref(false)
const message = ref('')
const error = ref('')
const registeredEmail = ref('')

async function submitSignup() {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const payload = { ...form.value }
    await createApiClient().signup(payload)
    registeredEmail.value = payload.email
    message.value = '가입이 완료되었습니다. 이메일과 비밀번호로 로그인해주세요.'
    form.value = { name: '', email: '', password: '' }
  } catch (requestError) {
    error.value = requestError.message || '회원가입에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <div class="page-heading">
      <span class="eyebrow"><i></i> CREATE YOUR ACCOUNT</span>
      <h1>기록을 시작할<br /><em>계정을 만들어보세요.</em></h1>
      <p>이름과 이메일을 등록하면 노트 작업 공간을 이용할 수 있어요.</p>
    </div>

    <PageSkeleton v-if="loading" variant="form" compact />
    <article v-else class="form-card auth-card">
      <div class="form-card-top"><div><span class="section-kicker">NEW MEMBER</span><h2>회원가입</h2></div><span class="route-index">01 / 05</span></div>
      <form class="api-form" @submit.prevent="submitSignup">
        <label>이름<input v-model.trim="form.name" name="name" autocomplete="name" placeholder="홍길동" required /></label>
        <label>이메일<input v-model.trim="form.email" name="email" type="email" autocomplete="email" placeholder="hello@example.com" required /></label>
        <label>비밀번호<input v-model="form.password" name="password" type="password" autocomplete="new-password" placeholder="비밀번호를 입력하세요" required /></label>
        <button class="primary-button" type="submit">계정 만들기 <span>↗</span></button>
      </form>
      <p v-if="message" class="form-message success" role="status">{{ message }} <RouterLink :to="{ name: 'login', query: { email: registeredEmail } }">로그인하기 →</RouterLink></p>
      <p v-if="error" class="form-message error" role="alert">{{ error }}</p>
      <p class="form-footnote">이미 계정이 있나요? <RouterLink :to="{ name: 'login' }">로그인</RouterLink></p>
    </article>
  </section>
</template>
