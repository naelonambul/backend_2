const REDIRECT_ORIGIN = 'https://haven.internal'

export function getSafeRedirectTarget(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return null
  if (/%5c/i.test(value) || /[\u0000-\u001f]/.test(value)) return null

  try {
    const target = new URL(value, REDIRECT_ORIGIN)
    if (target.origin !== REDIRECT_ORIGIN) return null
    return `${target.pathname}${target.search}${target.hash}`
  } catch {
    return null
  }
}
