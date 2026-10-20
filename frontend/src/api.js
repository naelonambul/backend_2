const LEGACY_DEFAULT_API_BASE_URLS = ['http://localhost:8000', 'http://127.0.0.1:8000']

function getDefaultApiBaseUrl() {
  return typeof __BACKEND_ORIGIN__ !== 'undefined'
    ? __BACKEND_ORIGIN__
    : 'http://127.0.0.1:8000'
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function normalizeBaseUrl(value) {
  return value.trim().replace(/\/+$/, '')
}

export function getConfiguredBaseUrl() {
  const defaultBaseUrl = getDefaultApiBaseUrl()
  if (typeof localStorage !== 'undefined') {
    const configuredBaseUrl = localStorage.getItem('note-api-base')
    if (configuredBaseUrl && LEGACY_DEFAULT_API_BASE_URLS.includes(normalizeBaseUrl(configuredBaseUrl))) {
      localStorage.setItem('note-api-base', defaultBaseUrl)
      return defaultBaseUrl
    }
    return configuredBaseUrl || defaultBaseUrl
  }
  return defaultBaseUrl
}

export function createApiClient(baseUrl = getConfiguredBaseUrl(), fetchImpl) {
  const base = normalizeBaseUrl(baseUrl)

  async function request(path, { method = 'GET', body } = {}) {
    const fetcher = fetchImpl ?? globalThis.fetch
    if (!fetcher) throw new Error('현재 브라우저에서 fetch를 사용할 수 없습니다.')

    const response = await fetcher(base + path, {
      method,
      credentials: 'include',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    let payload = null
    try {
      payload = await response.json()
    } catch {
      // Empty and non-JSON responses are represented as null.
    }

    if (!response.ok) {
      const detail = payload?.detail
      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join(', ')
        : typeof detail === 'string'
          ? detail
          : '요청을 처리하지 못했습니다. (' + response.status + ')'
      throw new ApiError(message, response.status)
    }

    return payload
  }

  return {
    ping: () => request('/'),
    signup: (data) => request('/user/signup', { method: 'POST', body: data }),
    login: (data) => request('/user/login', { method: 'POST', body: data }),
    getCurrentUser: () => request('/user/me'),
    logout: () => request('/user/logout', { method: 'POST' }),
    createKakaoState: () => request('/user/kakao/state', { method: 'POST' }),
    completeKakaoLogin: (data) => request('/user/kakao/callback', { method: 'POST', body: data }),
    registerBoard: (data) => request('/board/register', { method: 'POST', body: data }),
    listBoards: () => request('/board/list'),
    readBoard: (idx) => request('/board/read/' + encodeURIComponent(idx)),
    listProperties: () => request('/properties'),
    readProperty: (idx) => request('/properties/' + encodeURIComponent(idx)),
    registerProperty: (data) => request('/properties', { method: 'POST', body: data }),
  }
}
