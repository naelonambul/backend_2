export const PROPERTY_PURCHASE_SESSION_KEY = 'property-purchase-id'
export const PROPERTY_PURCHASE_PAYMENT_SESSION_KEY = 'property-purchase-payment-id'

function clearPurchaseSession(sessionStorage) {
  try {
    sessionStorage?.removeItem(PROPERTY_PURCHASE_SESSION_KEY)
    sessionStorage?.removeItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY)
  } catch { /* Storage may be unavailable. */ }
}

function isRetryable(error) {
  const status = error?.status
  return status == null || status === 408 || status === 425 || status === 429 || status >= 500
}

function resolveConfirmedPurchase(result, sessionStorage) {
  if (result?.status === 'pending') return { state: 'pending', ...result }
  if (result?.status === 'refund_pending') return { state: 'refund_pending', ...result }
  if (result?.status === 'paid') {
    clearPurchaseSession(sessionStorage)
    return { state: 'success', ...result }
  }
  if (result?.status === 'failed' || result?.status === 'cancelled' || result?.status === 'expired') {
    clearPurchaseSession(sessionStorage)
    return { state: result.status === 'cancelled' ? 'cancelled' : 'failed', ...result }
  }
  return { state: 'retryable-error', ...result, error: new Error('결제 결과를 확인하지 못했습니다. 다시 확인해 주세요.') }
}

async function confirmWithBackend({ api, purchaseId, paymentId, sessionStorage, retainOnTerminalError = false }) {
  try {
    const result = await api.confirmPurchase(purchaseId, { payment_id: paymentId })
    return resolveConfirmedPurchase(result, sessionStorage)
  } catch (error) {
    if (isRetryable(error)) return { state: 'retryable-error', error }
    if (retainOnTerminalError) return { state: 'retryable-error', error }
    clearPurchaseSession(sessionStorage)
    return { state: 'terminal-error', error }
  }
}

async function verifyCancelledOrder({ api, purchaseId, paymentId, sessionStorage }) {
  const result = await confirmWithBackend({ api, purchaseId, paymentId, sessionStorage, retainOnTerminalError: true })
  return result.state === 'failed' ? { ...result, state: 'cancelled' } : result
}

export function canStartPropertyPurchase({ role, availability }) {
  return role === 'buyer' && availability === 'available'
}

export function canRetryPropertyPurchase(state) {
  return state === 'pending' || state === 'retryable-error' || state === 'refund_pending'
}

export async function startPropertyPurchase({
  propertyIdx,
  api,
  portone,
  storeId,
  channelKey,
  redirectUrl,
  sessionStorage,
}) {
  if (!storeId || !channelKey) {
    const error = new Error('결제 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.')
    error.code = 'PORTONE_CONFIG_MISSING'
    throw error
  }

  let unresolvedPurchaseId = null
  try { unresolvedPurchaseId = sessionStorage?.getItem(PROPERTY_PURCHASE_SESSION_KEY) } catch { /* Storage may be unavailable. */ }
  if (unresolvedPurchaseId) {
    return { state: 'retryable-error', error: new Error('이전 결제 결과를 먼저 확인해 주세요.') }
  }

  const order = await api.createPurchase(propertyIdx)
  if (!order?.purchase_id || !order?.payment_id || !order?.order_name || !Number.isInteger(order?.amount) || order.amount <= 0 || order.currency !== 'KRW') {
    throw new Error('결제 주문 정보를 확인할 수 없습니다. 매물 가격을 확인해 주세요.')
  }

  sessionStorage.setItem(PROPERTY_PURCHASE_SESSION_KEY, order.purchase_id)
  sessionStorage.setItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY, order.payment_id)
  let response
  try {
    response = await portone.requestPayment({
      storeId,
      paymentId: order.payment_id,
      orderName: order.order_name,
      totalAmount: order.amount,
      currency: 'KRW',
      channelKey,
      payMethod: 'CARD',
      redirectUrl,
    })
  } catch (error) {
    if (error?.code === 'USER_CANCEL') {
      return verifyCancelledOrder({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
    }
    clearPurchaseSession(sessionStorage)
    throw error
  }

  if (response == null) return { state: 'redirecting', purchaseId: order.purchase_id }
  if (response.code) {
    if (response.code === 'USER_CANCEL') {
      return verifyCancelledOrder({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
    }
    clearPurchaseSession(sessionStorage)
    const error = new Error(response.message || '결제를 진행하지 못했습니다.')
    error.code = response.code
    throw error
  }
  if (!response.paymentId) {
    return verifyCancelledOrder({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
  }
  if (response.paymentId !== order.payment_id) {
    clearPurchaseSession(sessionStorage)
    return { state: 'terminal-error', error: new Error('결제 번호가 주문 정보와 일치하지 않습니다.') }
  }
  return confirmWithBackend({
    api,
    purchaseId: order.purchase_id,
    paymentId: response.paymentId,
    sessionStorage,
  })
}

export async function confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId }) {
  let purchaseId = null
  let savedPaymentId = null
  try {
    purchaseId = sessionStorage?.getItem(PROPERTY_PURCHASE_SESSION_KEY)
    savedPaymentId = sessionStorage?.getItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY)
  } catch { /* Storage may be unavailable. */ }
  if (!purchaseId) return { state: 'missing-order' }
  const resolvedPaymentId = savedPaymentId || (typeof paymentId === 'string' ? paymentId : null)
  if (typeof resolvedPaymentId !== 'string' || !resolvedPaymentId) {
    clearPurchaseSession(sessionStorage)
    return { state: 'cancelled' }
  }
  try { sessionStorage?.setItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY, resolvedPaymentId) } catch { /* The current confirmation can still proceed. */ }
  return confirmWithBackend({ api, purchaseId, paymentId: resolvedPaymentId, sessionStorage })
}
