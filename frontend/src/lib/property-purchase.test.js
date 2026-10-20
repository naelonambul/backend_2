import { createApiClient } from '../api'
import {
  canStartPropertyPurchase,
  canRetryPropertyPurchase,
  confirmPropertyPurchaseReturn,
  startPropertyPurchase,
} from './property-purchase'

const purchaseOrder = {
  purchase_id: 'purchase-123',
  payment_id: 'payment-123',
  order_name: 'Mapo home',
  amount: 720000000,
  currency: 'KRW',
  expires_at: '2026-10-20T09:15:00Z',
}

function makeStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
    values,
  }
}

describe('property purchase flow', () => {
  it('test_checkout_uses_server_order_amount_and_v2_channel_config', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'paid' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ paymentId: 'payment-123' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({
      propertyIdx: 42, api, portone, storeId: 'store-public', channelKey: 'channel-public',
      redirectUrl: 'https://market.example/properties/purchase/return', sessionStorage,
    })

    expect(api.createPurchase).toHaveBeenCalledWith(42)
    expect(portone.requestPayment).toHaveBeenCalledWith({
      storeId: 'store-public', paymentId: 'payment-123', orderName: 'Mapo home',
      totalAmount: 720000000, currency: 'KRW', channelKey: 'channel-public',
      payMethod: 'CARD', redirectUrl: 'https://market.example/properties/purchase/return',
    })
    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(result).toMatchObject({ state: 'success', status: 'paid' })
  })

  it('test_checkout_stores_purchase_id_for_redirect_return', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn() }
    const portone = { requestPayment: jest.fn().mockResolvedValue(undefined) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/properties/purchase/return', sessionStorage })

    expect(sessionStorage.values).toEqual(new Map([['property-purchase-id', 'purchase-123'], ['property-purchase-payment-id', 'payment-123']]))
    expect(api.confirmPurchase).not.toHaveBeenCalled()
    expect(result).toMatchObject({ state: 'redirecting', purchaseId: 'purchase-123' })
  })

  it('test_checkout_cancellation_does_not_show_success', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'failed' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ code: 'USER_CANCEL', message: 'cancelled' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/properties/purchase/return', sessionStorage })

    expect(result.state).toBe('cancelled')
    expect(result.state).not.toBe('success')
    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(sessionStorage.values.size).toBe(0)
  })

  it('does not replace an unresolved purchase when checkout starts on another listing', async () => {
    const api = { createPurchase: jest.fn(), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-old', status: 'pending' }) }
    const portone = { requestPayment: jest.fn() }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-old', 'property-purchase-payment-id': 'payment-old' })

    const blocked = await startPropertyPurchase({ propertyIdx: 88, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })
    const returned = await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-new' })

    expect(blocked.state).toBe('pending')
    expect(api.createPurchase).not.toHaveBeenCalled()
    expect(portone.requestPayment).not.toHaveBeenCalled()
    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-old', { payment_id: 'payment-old' })
    expect(returned.state).toBe('pending')
  })

  it('keeps a new checkout blocked when the backend still reports the saved order pending', async () => {
    const api = { createPurchase: jest.fn(), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-old', status: 'pending' }) }
    const portone = { requestPayment: jest.fn() }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-old', 'property-purchase-payment-id': 'payment-old' })

    const result = await startPropertyPurchase({ propertyIdx: 88, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-old', { payment_id: 'payment-old' })
    expect(api.createPurchase).not.toHaveBeenCalled()
    expect(portone.requestPayment).not.toHaveBeenCalled()
    expect(result.state).toBe('pending')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-old')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-old')
  })

  it('allows a new order after the backend confirms the previous order was cancelled', async () => {
    const newOrder = { ...purchaseOrder, purchase_id: 'purchase-new', payment_id: 'payment-new' }
    const api = {
      createPurchase: jest.fn().mockResolvedValue(newOrder),
      confirmPurchase: jest.fn()
        .mockResolvedValueOnce({ purchase_id: 'purchase-old', status: 'cancelled' })
        .mockResolvedValueOnce({ purchase_id: 'purchase-new', status: 'paid' }),
    }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ paymentId: 'payment-new' }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-old', 'property-purchase-payment-id': 'payment-old' })

    const result = await startPropertyPurchase({ propertyIdx: 88, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenNthCalledWith(1, 'purchase-old', { payment_id: 'payment-old' })
    expect(api.createPurchase).toHaveBeenCalledWith(88)
    expect(portone.requestPayment).toHaveBeenCalledWith(expect.objectContaining({ paymentId: 'payment-new' }))
    expect(result).toMatchObject({ state: 'success', status: 'paid' })
    expect(sessionStorage.values.size).toBe(0)
  })

  it('retains an unresolved pair when preflight verification fails', async () => {
    const api = { createPurchase: jest.fn(), confirmPurchase: jest.fn().mockRejectedValue(Object.assign(new Error('verification unavailable'), { status: 400 })) }
    const portone = { requestPayment: jest.fn() }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-old', 'property-purchase-payment-id': 'payment-old' })

    const result = await startPropertyPurchase({ propertyIdx: 88, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(api.createPurchase).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-old')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-old')
  })

  it('retains the paired identifiers when cancellation verification is pending', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'pending' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ code: 'USER_CANCEL' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(result.state).toBe('pending')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('retains the paired identifiers when cancellation verification fails', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockRejectedValue(Object.assign(new Error('server unavailable'), { status: 400 })) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ code: 'USER_CANCEL' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('verifies a missing SDK callback using the server payment id', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'failed' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({}) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(result.state).toBe('cancelled')
    expect(sessionStorage.values.size).toBe(0)
  })

  it('reconciles a thrown SDK error with the server payment id and preserves pending state', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'pending' }) }
    const portone = { requestPayment: jest.fn().mockRejectedValue(new Error('SDK transport failed')) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(result.state).toBe('pending')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('uses backend confirmation, not a non-cancel SDK response code, to determine success', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'paid' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ code: 'PAYMENT_DECLINED', message: 'declined' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(result).toMatchObject({ state: 'success', status: 'paid' })
    expect(sessionStorage.values.size).toBe(0)
  })

  it('ignores a mismatched browser payment id and reconciles only the server payment id', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'refund_pending' }) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ paymentId: 'payment-from-another-order' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/return', sessionStorage })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(api.confirmPurchase).not.toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-from-another-order' })
    expect(result.state).toBe('refund_pending')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('test_return_confirms_with_server_and_clears_session_on_terminal_result', async () => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'paid' }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-123' })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(sessionStorage.values.size).toBe(0)
    expect(result).toMatchObject({ state: 'success', status: 'paid' })
  })

  it('test_return_keeps_session_for_retryable_error', async () => {
    const api = { confirmPurchase: jest.fn().mockRejectedValue(Object.assign(new Error('temporary outage'), { status: 503 })) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-123' })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('preserves the purchase pair after a non-retryable HTTP verification error', async () => {
    const api = { confirmPurchase: jest.fn().mockRejectedValue(Object.assign(new Error('invalid confirmation'), { status: 400 })) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('retains an order and reports recovery when no saved or callback payment id exists', async () => {
    const api = { confirmPurchase: jest.fn() }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(api.confirmPurchase).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBeNull()
  })

  it.each(['pending', 'refund_pending'])('preserves a recoverable %s confirmation state', async (status) => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(result).toMatchObject({ state: status, status })
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('retains identifiers when the backend returns an unrecognized nonterminal status', async () => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'processing' }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')
  })

  it('stores a payment id returned in the redirect query before confirming', async () => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'pending' }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123' })

    await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-from-return' })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-from-return' })
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-from-return')
  })

  it.each(['failed', 'cancelled'])('clears saved identifiers after terminal %s status', async (status) => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123', 'property-purchase-payment-id': 'payment-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(result.state).toBe(status === 'cancelled' ? 'cancelled' : 'failed')
    expect(sessionStorage.values.size).toBe(0)
  })

  it('exposes a retry action for pending, retryable, and refund pending outcomes', () => {
    expect(canRetryPropertyPurchase('pending')).toBe(true)
    expect(canRetryPropertyPurchase('retryable-error')).toBe(true)
    expect(canRetryPropertyPurchase('refund_pending')).toBe(true)
    expect(canRetryPropertyPurchase('success')).toBe(false)
    expect(canRetryPropertyPurchase('cancelled')).toBe(false)
  })

  it('persists the payment id and retries the same order after a retryable confirmation error', async () => {
    const api = {
      createPurchase: jest.fn().mockResolvedValue(purchaseOrder),
      confirmPurchase: jest.fn()
        .mockRejectedValueOnce(Object.assign(new Error('temporary outage'), { status: 503 }))
        .mockResolvedValueOnce({ purchase_id: 'purchase-123', status: 'paid' }),
    }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ paymentId: 'payment-123' }) }
    const sessionStorage = makeStorage()

    const firstAttempt = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/properties/purchase/return', sessionStorage })

    expect(firstAttempt.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
    expect(sessionStorage.getItem('property-purchase-payment-id')).toBe('payment-123')

    const retry = await confirmPropertyPurchaseReturn({ api, sessionStorage })

    expect(api.confirmPurchase).toHaveBeenLastCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(retry).toMatchObject({ state: 'success', status: 'paid' })
    expect(sessionStorage.values.size).toBe(0)
  })

  it('test_seller_or_unavailable_listing_cannot_start_checkout', async () => {
    expect(canStartPropertyPurchase({ role: 'seller', availability: 'available' })).toBe(false)
    expect(canStartPropertyPurchase({ role: 'buyer', availability: 'reserved' })).toBe(false)
    expect(canStartPropertyPurchase({ role: 'buyer', availability: 'sold' })).toBe(false)
    expect(canStartPropertyPurchase({ role: 'buyer', availability: 'available' })).toBe(true)
  })

  it('test_missing_public_portone_config_shows_setup_error', async () => {
    const api = { createPurchase: jest.fn() }
    const portone = { requestPayment: jest.fn() }

    await expect(startPropertyPurchase({ propertyIdx: 1, api, portone, storeId: '', channelKey: 'channel', redirectUrl: '/return', sessionStorage: makeStorage() }))
      .rejects.toMatchObject({ code: 'PORTONE_CONFIG_MISSING' })
    expect(api.createPurchase).not.toHaveBeenCalled()
    expect(portone.requestPayment).not.toHaveBeenCalled()
  })

  it('uses cookie-backed API methods for order creation and confirmation', async () => {
    const responses = [purchaseOrder, { purchase_id: 'purchase-123', status: 'paid' }]
    const fetchMock = jest.fn().mockImplementation(async () => {
      const payload = responses.shift()
      return { ok: true, status: 200, json: async () => payload }
    })
    const api = createApiClient('https://api.example', fetchMock)

    await api.createPurchase(42)
    await api.confirmPurchase('purchase/123', { payment_id: 'payment-123' })

    expect(fetchMock).toHaveBeenNthCalledWith(1, 'https://api.example/properties/42/purchases', {
      method: 'POST', credentials: 'include', headers: undefined, body: undefined,
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'https://api.example/purchases/purchase%2F123/confirm', {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_id: 'payment-123' }),
    })
  })

  it('does not clear a retryable direct confirmation result', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn().mockRejectedValue(new Error('network unavailable')) }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ paymentId: 'payment-123' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/properties/purchase/return', sessionStorage })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
  })
})
