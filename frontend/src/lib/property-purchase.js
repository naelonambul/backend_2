export const PROPERTY_PURCHASE_SESSION_KEY = 'property-purchase-id'

function clearPurchaseSession(sessionStorage) {
  try { sessionStorage?.removeItem(PROPERTY_PURCHASE_SESSION_KEY) } catch { /* Storage may be unavailable. */ }
}

function isRetryable(error) {
  const status = error?.status
  return status == null || status === 408 || status === 425 || status === 429 || status >= 500
}

function resolveConfirmedPurchase(result, sessionStorage) {
  if (result?.status === 'pending') return { state: 'pending', ...result }
  clearPurchaseSession(sessionStorage)
  if (result?.status === 'paid') return { state: 'success', ...result }
  return { state: 'failed', ...result }
}

async function confirmWithBackend({ api, purchaseId, paymentId, sessionStorage }) {
  try {
    const result = await api.confirmPurchase(purchaseId, { payment_id: paymentId })
    return resolveConfirmedPurchase(result, sessionStorage)
  } catch (error) {
    if (isRetryable(error)) return { state: 'retryable-error', error }
    clearPurchaseSession(sessionStorage)
    return { state: 'terminal-error', error }
  }
}

export function canStartPropertyPurchase({ role, availability }) {
  return role === 'buyer' && availability === 'available'
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

  const order = await api.createPurchase(propertyIdx)
  if (!Number.isInteger(order?.amount) || order.amount <= 0 || order.currency !== 'KRW') {
    throw new Error('결제 주문 정보를 확인할 수 없습니다. 매물 가격을 확인해 주세요.')
  }

  sessionStorage.setItem(PROPERTY_PURCHASE_SESSION_KEY, order.purchase_id)
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
    clearPurchaseSession(sessionStorage)
    if (error?.code === 'USER_CANCEL') return { state: 'cancelled' }
    throw error
  }

  if (response == null) return { state: 'redirecting', purchaseId: order.purchase_id }
  if (response.code) {
    clearPurchaseSession(sessionStorage)
    if (response.code === 'USER_CANCEL') return { state: 'cancelled' }
    const error = new Error(response.message || '결제를 진행하지 못했습니다.')
    error.code = response.code
    throw error
  }
  if (!response.paymentId) return { state: 'retryable-error', error: new Error('결제 결과를 확인하지 못했습니다. 잠시 후 다시 확인해 주세요.') }

  return confirmWithBackend({
    api,
    purchaseId: order.purchase_id,
    paymentId: response.paymentId,
    sessionStorage,
  })
}

export async function confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId }) {
  let purchaseId = null
  try { purchaseId = sessionStorage?.getItem(PROPERTY_PURCHASE_SESSION_KEY) } catch { /* Storage may be unavailable. */ }
  if (!purchaseId) return { state: 'missing-order' }
  if (typeof paymentId !== 'string' || !paymentId) {
    clearPurchaseSession(sessionStorage)
    return { state: 'cancelled' }
  }
  return confirmWithBackend({ api, purchaseId, paymentId, sessionStorage })
}
