<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { createApiClient } from '../api'
import { exchangeKakaoCode, getKakaoCallbackError } from '../auth/kakao'

const route = useRoute()
const router = useRouter()
const error = ref('')

onMounted(async () => {
  error.value = getKakaoCallbackError(route.query)
  if (error.value) return

  try {
    await exchangeKakaoCode({
      code: typeof route.query.code === 'string' ? route.query.code : '',
      state: typeof route.query.state === 'string' ? route.query.state : '',
      api: createApiClient(),
    })
    await router.replace({ name: 'login' })
  } catch (requestError) {
    error.value = requestError.message || '카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.'
  }
})
</script>

<template>
  <section class="auth-page auth-page--callback" aria-labelledby="kakao-callback-title">
    <div class="auth-card">
      <p class="section-label">카카오 로그인</p>
      <h1 id="kakao-callback-title">{{ error ? '로그인을 마치지 못했어요' : '로그인 확인 중' }}</h1>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p v-else class="auth-copy" role="status">카카오 계정을 확인하고 있습니다.</p>
      <RouterLink v-if="error" class="button-primary button-primary--wide callback-login-link" :to="{ name: 'login' }">
        로그인으로 돌아가기
      </RouterLink>
    </div>
  </section>
</template>
