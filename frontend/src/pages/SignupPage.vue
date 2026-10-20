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
  } catch (requestError) {
    error.value = requestError.message || '가입을 완료하지 못했습니다.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="auth-page" aria-labelledby="signup-title">
    <div class="auth-aside auth-aside--butter">
      <span class="auth-aside__mark" aria-hidden="true">✳</span>
      <p>생각이 머물 자리를<br />새로 만들어 보세요.</p>
      <span class="auth-aside__caption">첫 페이지는 금방 시작돼요</span>
    </div>
    <div class="auth-card">
      <p class="section-label">새로운 시작</p>
      <h1 id="signup-title">회원가입</h1>
      <p class="auth-copy">당신의 기록을 위한 공간을 만들어요.</p>
      <form class="auth-form" @submit.prevent="submitSignup">
        <label class="field-label" for="signup-name">이름</label>
        <input id="signup-name" v-model.trim="form.name" type="text" autocomplete="name" placeholder="이름을 입력하세요" required />
        <label class="field-label" for="signup-email">이메일</label>
        <input id="signup-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" required />
        <label class="field-label" for="signup-password">비밀번호</label>
        <input id="signup-password" v-model="form.password" type="password" autocomplete="new-password" minlength="1" placeholder="비밀번호를 입력하세요" required />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="button-primary button-primary--wide" type="submit" :disabled="submitting">
          {{ submitting ? '가입 중…' : '계정 만들기' }} <span aria-hidden="true">↗</span>
        </button>
      </form>
      <p class="auth-switch">이미 계정이 있나요? <RouterLink :to="{ name: 'login' }">로그인</RouterLink></p>
    </div>
  </section>
</template>
