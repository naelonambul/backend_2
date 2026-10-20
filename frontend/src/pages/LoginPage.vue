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
  try {
    currentUser.value = await getCurrentUserOrNull(api)
  } catch (requestError) {
    sessionError.value = requestError.message || '로그인 상태를 확인하지 못했습니다.'
  } finally {
    sessionLoading.value = false
  }
})

async function submitLogin() {
  error.value = ''
  submitting.value = true
  try {
    await api.login(form.value)
    currentUser.value = await api.getCurrentUser()
  } catch (requestError) {
    error.value = requestError.message || '로그인하지 못했습니다.'
  } finally {
    submitting.value = false
  }
}

async function submitLogout() {
  sessionError.value = ''
  logoutSubmitting.value = true
  try {
    await api.logout()
    currentUser.value = null
  } catch (requestError) {
    sessionError.value = requestError.message || '로그아웃하지 못했습니다.'
  } finally {
    logoutSubmitting.value = false
  }
}

async function submitKakaoLogin() {
  error.value = ''
  kakaoSubmitting.value = true
  try {
    const frontendOrigin = typeof __FRONTEND_ORIGIN__ !== 'undefined'
      ? __FRONTEND_ORIGIN__
      : window.location.origin
    const redirectUri = import.meta.env.VITE_KAKAO_REDIRECT_URI || `${frontendOrigin}/auth/kakao/callback`
    await beginKakaoLogin({
      sdk: window.Kakao,
      javascriptKey: import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY,
      redirectUri,
      api,
    })
  } catch (requestError) {
    error.value = requestError.message || '카카오 로그인을 시작하지 못했습니다.'
  } finally {
    kakaoSubmitting.value = false
  }
}
</script>

<template>
  <section class="auth-page" aria-labelledby="login-title">
    <div class="auth-aside auth-aside--mint">
      <span class="auth-aside__mark" aria-hidden="true">“</span>
      <p>나중의 내가<br />고마워할 기록을 모아요.</p>
      <span class="auth-aside__caption">모아 노트에 오신 걸 환영해요</span>
    </div>
    <div class="auth-card">
      <template v-if="sessionLoading">
        <p class="section-label">계정 확인</p>
        <h1 id="login-title">잠시만요</h1>
        <p class="auth-copy" role="status">로그인 상태를 확인하고 있어요.</p>
      </template>
      <template v-else-if="currentUser">
        <p class="section-label">내 계정</p>
        <h1 id="login-title">로그인 완료</h1>
        <p class="auth-copy">{{ currentUser.name }}님, 로그인된 계정 정보입니다.</p>
        <dl class="account-details">
          <div class="account-details__row">
            <dt>이름</dt>
            <dd>{{ currentUser.name }}</dd>
          </div>
          <div class="account-details__row">
            <dt>이메일</dt>
            <dd>{{ currentUser.email || '제공되지 않음' }}</dd>
          </div>
          <div class="account-details__row">
            <dt>로그인 방식</dt>
            <dd>{{ currentUser.provider === 'kakao' ? '카카오' : '이메일' }}</dd>
          </div>
        </dl>
        <p v-if="sessionError" class="form-error" role="alert">{{ sessionError }}</p>
        <div class="account-actions">
          <RouterLink class="button-primary button-primary--wide" :to="{ name: 'board-list' }">보관함으로 가기</RouterLink>
          <button class="button-secondary" type="button" :disabled="logoutSubmitting" @click="submitLogout">
            {{ logoutSubmitting ? '로그아웃 중…' : '로그아웃' }}
          </button>
        </div>
      </template>
      <template v-else>
        <p class="section-label">다시 만나기</p>
        <h1 id="login-title">로그인</h1>
        <p class="auth-copy">계정에 로그인하고 기록을 이어가세요.</p>
        <p v-if="justCreated" class="form-success" role="status">가입이 완료됐어요. 이제 로그인해 주세요.</p>
        <p v-if="sessionError" class="form-error" role="alert">{{ sessionError }}</p>
        <form class="auth-form" @submit.prevent="submitLogin">
          <label class="field-label" for="login-email">이메일</label>
          <input id="login-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" required />
          <label class="field-label" for="login-password">비밀번호</label>
          <input id="login-password" v-model="form.password" type="password" autocomplete="current-password" placeholder="비밀번호를 입력하세요" required />
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button class="button-primary button-primary--wide" type="submit" :disabled="submitting">
            {{ submitting ? '확인 중…' : '로그인' }} <span aria-hidden="true">↗</span>
          </button>
        </form>
        <div class="auth-divider" aria-hidden="true"><span>또는</span></div>
        <button class="button-kakao" type="button" :disabled="kakaoSubmitting" @click="submitKakaoLogin">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 3.5c-5.25 0-9.5 3.37-9.5 7.53 0 2.64 1.84 4.96 4.62 6.31l-.95 3.48c-.08.29.24.52.5.36l4.05-2.65c.42.06.84.09 1.28.09 5.25 0 9.5-3.37 9.5-7.53S17.25 3.5 12 3.5Z" />
          </svg>
          {{ kakaoSubmitting ? '카카오 연결 중…' : '카카오로 로그인' }}
        </button>
        <p class="auth-switch">아직 계정이 없나요? <RouterLink :to="{ name: 'signup' }">회원가입</RouterLink></p>
      </template>
    </div>
  </section>
</template>
