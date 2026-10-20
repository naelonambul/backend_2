<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { createApiClient } from '../api'
import { confirmPropertyPurchaseReturn } from '../lib/property-purchase'

const route = useRoute()
const api = createApiClient()
const state = ref('loading')
const message = ref('결제 결과를 확인하고 있어요.')
const paymentId = typeof route.query.paymentId === 'string'
  ? route.query.paymentId
  : typeof route.query.payment_id === 'string'
    ? route.query.payment_id
    : ''

async function confirmReturn() {
  state.value = 'loading'
  message.value = '결제 결과를 확인하고 있어요.'
  const result = await confirmPropertyPurchaseReturn({ api, sessionStorage: window.sessionStorage, paymentId })
  state.value = result.state
  if (result.state === 'success') message.value = '결제가 완료되었습니다.'
  else if (result.state === 'failed') message.value = '결제가 완료되지 않았습니다. 매물 목록에서 상태를 확인해 주세요.'
  else if (result.state === 'pending') message.value = '결제 확인이 진행 중입니다. 잠시 후 다시 확인해 주세요.'
  else if (result.state === 'refund_pending') message.value = '결제는 승인되었지만 환불 확인이 진행 중입니다. 다시 확인해 주세요.'
  else if (result.state === 'retryable-error') message.value = '일시적인 오류로 결제 결과를 확인하지 못했습니다. 다시 시도해 주세요.'
  else if (result.state === 'terminal-error') message.value = result.error?.message || '결제 결과를 확인하지 못했습니다.'
  else if (result.state === 'cancelled') message.value = '결제가 취소되었습니다.'
  else message.value = '확인할 결제 주문이 없습니다. 매물 상세 페이지에서 다시 시도해 주세요.'
}

onMounted(confirmReturn)
</script>

<template>
  <section class="purchase-return-page" aria-labelledby="purchase-return-title">
    <div class="purchase-return-card">
      <span class="purchase-return-card__mark" aria-hidden="true">{{ state === 'success' ? '✓' : state === 'loading' ? '…' : '⌂' }}</span>
      <p class="section-label">하벤 홈 결제</p>
      <h1 id="purchase-return-title">{{ state === 'success' ? '구매가 완료되었어요' : state === 'loading' ? '결제 확인 중' : state === 'cancelled' ? '결제가 취소되었어요' : state === 'refund_pending' ? '환불 확인 중' : '결제 상태 확인' }}</h1>
      <p :class="state === 'terminal-error' || state === 'refund_pending' ? 'form-error' : 'auth-copy'" :role="state === 'loading' ? 'status' : state.includes('error') || state === 'refund_pending' ? 'alert' : 'status'">{{ message }}</p>
      <button v-if="state === 'retryable-error' || state === 'pending' || state === 'refund_pending'" class="button-primary" type="button" @click="confirmReturn">결제 다시 확인</button>
      <RouterLink class="button-secondary" :to="{ name: 'property-list' }">매물 목록으로</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.purchase-return-page { display: grid; min-height: 58vh; place-items: center; padding: 48px 0; }
.purchase-return-card { display: flex; width: min(100%, 500px); flex-direction: column; align-items: center; padding: 44px 35px; border: 1px solid var(--line); border-radius: 20px; background: var(--surface); box-shadow: var(--shadow-soft); text-align: center; }
.purchase-return-card__mark { display: grid; width: 56px; height: 56px; place-items: center; margin-bottom: 22px; border-radius: 50%; background: var(--mint); color: #4c7564; font-size: 26px; }
.purchase-return-card h1 { margin: 3px 0 0; color: var(--ink-strong); font-size: 28px; letter-spacing: -.05em; }
.purchase-return-card .auth-copy,.purchase-return-card .form-error { margin: 13px 0 20px; }
.purchase-return-card .button-primary,.purchase-return-card .button-secondary { margin-top: 10px; }

@media (max-width: 640px) {
  .purchase-return-card { padding: 35px 22px; }
}
</style>
