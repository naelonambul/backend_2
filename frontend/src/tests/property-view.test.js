import {
  formatArea,
  formatPrice,
  getPropertyListState,
  getSellerAccessState,
  validatePropertyForm,
} from '../stores/property/view'

const validListing = {
  title: 'Sunny apartment',
  address: 'Seoul, Mapo-gu',
  price_krw: '500000000',
  area_m2: '84.5',
  room_count: '3',
  description: 'A bright home near the park.',
  image_url: '',
}

describe('property presentation helpers', () => {
  it('formats Korean won with grouped digits', () => {
    expect(formatPrice(1250000000)).toBe('₩1,250,000,000')
  })

  it('formats area in square metres', () => {
    expect(formatArea(84.5)).toBe('84.5 m²')
  })

  it.each([
    [{ loading: true, error: '', properties: [] }, 'loading'],
    [{ loading: false, error: 'offline', properties: [] }, 'error'],
    [{ loading: false, error: '', properties: [] }, 'empty'],
    [{ loading: false, error: '', properties: [{ idx: 1 }] }, 'ready'],
  ])('selects the listing state %s', (input, expected) => {
    expect(getPropertyListState(input)).toBe(expected)
  })

  it.each([
    [{ loading: true, error: '', role: null }, 'loading'],
    [{ loading: false, error: 'offline', role: null }, 'error'],
    [{ loading: false, error: '', role: 'seller' }, 'seller'],
    [{ loading: false, error: '', role: 'buyer' }, 'buyer'],
    [{ loading: false, error: '', role: null }, 'guest'],
  ])('selects seller access state %s', (input, expected) => {
    expect(getSellerAccessState(input)).toBe(expected)
  })

  it('accepts a valid listing form and normalizes numeric fields', () => {
    expect(validatePropertyForm(validListing)).toEqual({
      valid: true,
      errors: {},
      data: { ...validListing, price_krw: 500000000, area_m2: 84.5, room_count: 3, image_url: null },
    })
  })

  it('rejects missing text, negative price, non-positive area, and negative room count', () => {
    const result = validatePropertyForm({
      ...validListing, title: ' ', address: '', price_krw: '-1', area_m2: '0', room_count: '-2', description: '',
    })
    expect(result.valid).toBe(false)
    expect(result.errors).toMatchObject({
      title: expect.any(String), address: expect.any(String), price_krw: expect.any(String),
      area_m2: expect.any(String), room_count: expect.any(String), description: expect.any(String),
    })
  })

  it('rejects non-integer values and non-HTTP image URLs', () => {
    const result = validatePropertyForm({
      ...validListing, price_krw: '1.5', room_count: '2.2', image_url: 'javascript:alert(1)',
    })
    expect(result.valid).toBe(false)
    expect(result.errors).toMatchObject({
      price_krw: expect.any(String), room_count: expect.any(String), image_url: expect.any(String),
    })
  })
})
