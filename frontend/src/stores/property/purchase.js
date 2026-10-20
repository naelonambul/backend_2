export const PROPERTY_PURCHASE_SESSION_KEY = 'property-purchase-id'
export const PROPERTY_PURCHASE_PAYMENT_SESSION_KEY = 'property-purchase-payment-id'

function clearPurchaseSession(sessionStorage) {
  try {
    sessionStorage?.removeItem(PROPERTY_PURCHASE_SESSION_KEY)
    sessionStorage?.removeItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY)
  } catch { /* Storage may be unavailable. */ }
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

async function confirmWithBackend({ api, purchaseId, paymentId, sessionStorage }) {
  try {
    const result = await api.confirmPurchase(purchaseId, { payment_id: paymentId })
    return resolveConfirmedPurchase(result, sessionStorage)
  } catch (error) {
    return { state: 'retryable-error', error }
  }
}

async function reconcileOrderWithBackend({ api, purchaseId, paymentId, sessionStorage }) {
  return confirmWithBackend({ api, purchaseId, paymentId, sessionStorage })
}

async function verifyCancelledOrder({ api, purchaseId, paymentId, sessionStorage }) {
  const result = await reconcileOrderWithBackend({ api, purchaseId, paymentId, sessionStorage })
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
  let unresolvedPaymentId = null
  try { unresolvedPurchaseId = sessionStorage?.getItem(PROPERTY_PURCHASE_SESSION_KEY) } catch { /* Storage may be unavailable. */ }
  if (unresolvedPurchaseId) {
    try { unresolvedPaymentId = sessionStorage?.getItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY) } catch { /* Storage may be unavailable. */ }
    if (!unresolvedPaymentId) return { state: 'retryable-error', error: new Error('이전 결제 결과를 먼저 확인해 주세요.') }
    const priorPurchase = await confirmPropertyPurchaseReturn({ api, sessionStorage })
    if (priorPurchase.state !== 'failed' && priorPurchase.state !== 'cancelled') return priorPurchase
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
    return reconcileOrderWithBackend({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
  }

  if (response == null) return { state: 'redirecting', purchaseId: order.purchase_id }
  if (response.code) {
    if (response.code === 'USER_CANCEL') {
      return verifyCancelledOrder({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
    }
    return reconcileOrderWithBackend({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
  }
  if (!response.paymentId) {
    return verifyCancelledOrder({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
  }
  if (response.paymentId !== order.payment_id) {
    return reconcileOrderWithBackend({ api, purchaseId: order.purchase_id, paymentId: order.payment_id, sessionStorage })
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
    return { state: 'retryable-error', error: new Error('결제 번호를 확인할 수 없어 이전 주문을 보관했습니다.') }
  }
  try { sessionStorage?.setItem(PROPERTY_PURCHASE_PAYMENT_SESSION_KEY, resolvedPaymentId) } catch { /* The current confirmation can still proceed. */ }
  return confirmWithBackend({ api, purchaseId, paymentId: resolvedPaymentId, sessionStorage })
}
