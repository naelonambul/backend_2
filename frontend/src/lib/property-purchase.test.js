import { createApiClient } from '../api'
import {
  canStartPropertyPurchase,
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

    expect(sessionStorage.values).toEqual(new Map([['property-purchase-id', 'purchase-123']]))
    expect(api.confirmPurchase).not.toHaveBeenCalled()
    expect(result).toMatchObject({ state: 'redirecting', purchaseId: 'purchase-123' })
  })

  it('test_checkout_cancellation_does_not_show_success', async () => {
    const api = { createPurchase: jest.fn().mockResolvedValue(purchaseOrder), confirmPurchase: jest.fn() }
    const portone = { requestPayment: jest.fn().mockResolvedValue({ code: 'USER_CANCEL', message: 'cancelled' }) }
    const sessionStorage = makeStorage()

    const result = await startPropertyPurchase({ propertyIdx: 9, api, portone, storeId: 'store', channelKey: 'channel', redirectUrl: '/properties/purchase/return', sessionStorage })

    expect(result.state).toBe('cancelled')
    expect(result.state).not.toBe('success')
    expect(api.confirmPurchase).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('property-purchase-id')).toBeNull()
  })

  it('test_return_confirms_with_server_and_clears_session_on_terminal_result', async () => {
    const api = { confirmPurchase: jest.fn().mockResolvedValue({ purchase_id: 'purchase-123', status: 'paid' }) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-123' })

    expect(api.confirmPurchase).toHaveBeenCalledWith('purchase-123', { payment_id: 'payment-123' })
    expect(sessionStorage.getItem('property-purchase-id')).toBeNull()
    expect(result).toMatchObject({ state: 'success', status: 'paid' })
  })

  it('test_return_keeps_session_for_retryable_error', async () => {
    const api = { confirmPurchase: jest.fn().mockRejectedValue(Object.assign(new Error('temporary outage'), { status: 503 })) }
    const sessionStorage = makeStorage({ 'property-purchase-id': 'purchase-123' })

    const result = await confirmPropertyPurchaseReturn({ api, sessionStorage, paymentId: 'payment-123' })

    expect(result.state).toBe('retryable-error')
    expect(sessionStorage.getItem('property-purchase-id')).toBe('purchase-123')
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
