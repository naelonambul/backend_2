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

  if (!title || title.length > 200) errors.title = '제목을 1자 이상 200자 이하로 입력해 주세요.'
  if (!address || address.length > 300) errors.address = '주소를 1자 이상 300자 이하로 입력해 주세요.'
  if (!description || description.length > 5000) errors.description = '매물 설명을 1자 이상 5000자 이하로 입력해 주세요.'
  if (!/^\d+$/.test(price)) errors.price_krw = '매매가는 0 이상의 정수로 입력해 주세요.'
  if (!area || !Number.isFinite(Number(area)) || Number(area) <= 0) errors.area_m2 = '면적은 0보다 큰 숫자로 입력해 주세요.'
  if (!/^\d+$/.test(rooms)) errors.room_count = '방 개수는 0 이상의 정수로 입력해 주세요.'

  if (imageUrl) {
    try {
      const parsedUrl = new URL(imageUrl)
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) throw new Error('Invalid protocol')
    } catch {
      errors.image_url = 'HTTP 또는 HTTPS 형식의 사진 주소를 입력해 주세요.'
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
