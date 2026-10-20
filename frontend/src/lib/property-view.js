const currencyFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

export function formatPrice(priceKrw) {
  return `₩${currencyFormatter.format(Number(priceKrw) || 0)}`
}

export function formatArea(areaM2) {
  return `${Number(areaM2)} m²`
}

export function getPropertyListState({ loading, error, properties }) {
  if (loading) return 'loading'
  if (error) return 'error'
  return properties.length ? 'ready' : 'empty'
}

export function getSellerAccessState({ loading, error, role }) {
  if (loading) return 'loading'
  if (error) return 'error'
  if (role === 'seller') return 'seller'
  return role ? 'buyer' : 'guest'
}

export function validatePropertyForm(data) {
  const errors = {}
  const title = String(data.title ?? '').trim()
  const address = String(data.address ?? '').trim()
  const description = String(data.description ?? '').trim()
  const price = String(data.price_krw ?? '').trim()
  const area = String(data.area_m2 ?? '').trim()
  const rooms = String(data.room_count ?? '').trim()
  const imageUrl = String(data.image_url ?? '').trim()

  if (!title || title.length > 200) errors.title = 'Enter a title between 1 and 200 characters.'
  if (!address || address.length > 300) errors.address = 'Enter an address between 1 and 300 characters.'
  if (!description || description.length > 5000) errors.description = 'Enter a description between 1 and 5000 characters.'
  if (!/^\d+$/.test(price)) errors.price_krw = 'Price must be a non-negative whole number.'
  if (!area || !Number.isFinite(Number(area)) || Number(area) <= 0) errors.area_m2 = 'Area must be greater than zero.'
  if (!/^\d+$/.test(rooms)) errors.room_count = 'Room count must be a non-negative whole number.'

  if (imageUrl) {
    try {
      const parsedUrl = new URL(imageUrl)
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) throw new Error('Invalid protocol')
    } catch {
      errors.image_url = 'Enter a valid HTTP or HTTPS image URL.'
    }
  }

  if (Object.keys(errors).length) return { valid: false, errors }
  return {
    valid: true,
    errors,
    data: {
      ...data,
      title,
      address,
      description,
      price_krw: Number(price),
      area_m2: Number(area),
      room_count: Number(rooms),
      image_url: imageUrl || null,
    },
  }
}
