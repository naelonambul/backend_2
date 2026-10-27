import { ApiError, createApiClient, getConfiguredBaseUrl, normalizeBaseUrl } from '../api/api'

function makeResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  }
}

describe('note API client', () => {
  it('migrates the previous localhost default to the HTTPS API domain', () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
    const values = new Map([['note-api-base', 'http://localhost:8000']])
    const storage = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    }
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: storage })

    try {
      expect(getConfiguredBaseUrl()).toBe('https://api.nenene.n-e.kr')
      expect(values.get('note-api-base')).toBe('https://api.nenene.n-e.kr')
    } finally {
      if (originalLocalStorage) {
        Object.defineProperty(globalThis, 'localStorage', originalLocalStorage)
      } else {
        delete globalThis.localStorage
      }
    }
  })

  it('migrates the previous backend IP to the HTTPS API domain', () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
    const values = new Map([['note-api-base', 'http://100.100.100.20:8000']])
    const storage = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    }
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: storage })

    try {
      expect(getConfiguredBaseUrl()).toBe('https://api.nenene.n-e.kr')
      expect(values.get('note-api-base')).toBe('https://api.nenene.n-e.kr')
    } finally {
      if (originalLocalStorage) {
        Object.defineProperty(globalThis, 'localStorage', originalLocalStorage)
      } else {
        delete globalThis.localStorage
      }
    }
  })

  it('uses the HTTPS API domain by default', () => {
    const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
    const storage = { getItem: () => null, setItem: jest.fn() }
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: storage })

    try {
      expect(getConfiguredBaseUrl()).toBe('https://api.nenene.n-e.kr')
    } finally {
      if (originalLocalStorage) {
        Object.defineProperty(globalThis, 'localStorage', originalLocalStorage)
      } else {
        delete globalThis.localStorage
      }
    }
  })

  it('uses BACKEND_ORIGIN as the API base when configured by the frontend build', () => {
    const originalBackendOrigin = Object.getOwnPropertyDescriptor(globalThis, '__BACKEND_ORIGIN__')
    Object.defineProperty(globalThis, '__BACKEND_ORIGIN__', {
      configurable: true,
      value: 'http://127.0.0.1:8001',
    })

    try {
      expect(getConfiguredBaseUrl()).toBe('http://127.0.0.1:8001')
    } finally {
      if (originalBackendOrigin) {
        Object.defineProperty(globalThis, '__BACKEND_ORIGIN__', originalBackendOrigin)
      } else {
        delete globalThis.__BACKEND_ORIGIN__
      }
    }
  })

  it('normalizes the configured server URL', () => {
    expect(normalizeBaseUrl('  http://localhost:8000///  ')).toBe('http://localhost:8000')
  })

  it('posts signup data as JSON and includes cookies', async () => {
    const data = { email: 'moa@example.com', name: '모아', password: 'secret' }
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, { email: data.email, name: data.name }))
    const client = createApiClient('http://localhost:8000/', fetchMock)

    await expect(client.signup(data)).resolves.toEqual({ email: data.email, name: data.name })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/user/signup', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  })

  it('requests a Kakao state and exchanges the authorization code', async () => {
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(200, { state: 'csrf-state' }))
      .mockResolvedValueOnce(makeResponse(200, { ok: true }))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.createKakaoState()).resolves.toEqual({ state: 'csrf-state' })
    await expect(client.completeKakaoLogin({ code: 'oauth-code', state: 'csrf-state' }))
      .resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://localhost:8000/user/kakao/state', {
      method: 'POST', credentials: 'include', headers: undefined, body: undefined,
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://localhost:8000/user/kakao/callback', {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: 'oauth-code', state: 'csrf-state' }),
    })
  })

  it('reads the signed-in user and logs out through cookie-backed requests', async () => {
    const profile = { name: '모아', email: 'moa@example.com', provider: 'email' }
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(200, profile))
      .mockResolvedValueOnce(makeResponse(200, { ok: true }))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.getCurrentUser()).resolves.toEqual(profile)
    await expect(client.logout()).resolves.toEqual({ ok: true })

    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://localhost:8000/user/me', {
      method: 'GET', credentials: 'include', headers: undefined, body: undefined,
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'http://localhost:8000/user/logout', {
      method: 'POST', credentials: 'include', headers: undefined, body: undefined,
    })
  })

  it('reads a board entry by its encoded index', async () => {
    const note = { idx: 7, title: '첫 기록', contents: '내용' }
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, note))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.readBoard(7)).resolves.toEqual(note)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/board/read/7', {
      method: 'GET',
      credentials: 'include',
      headers: undefined,
      body: undefined,
    })
  })

  it('loads the board collection from the list endpoint', async () => {
    const rows = [{ idx: 3, title: '세 번째', contents: '최근 글' }]
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, rows))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.listBoards()).resolves.toEqual(rows)
  })

  it('turns FastAPI validation errors into a readable message', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(422, {
      detail: [{ msg: 'Field required' }, { msg: 'Invalid email' }],
    }))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.ping()).rejects.toMatchObject({
      name: 'ApiError',
      message: 'Field required, Invalid email',
      status: 422,
    })
  })

  it('uses the HTTP status when the server has no detail message', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(503, {}))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.login({ email: 'a@b.com', password: 'x' })).rejects.toBeInstanceOf(ApiError)
    await expect(client.login({ email: 'a@b.com', password: 'x' })).rejects.toMatchObject({
      message: '요청을 처리하지 못했습니다. (503)',
      status: 503,
    })
  })
})

describe('property API methods', () => {
  it('lists properties from the public collection endpoint', async () => {
    const rows = [{ idx: 3, title: 'Sunny apartment' }]
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, rows))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.listProperties()).resolves.toEqual(rows)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/properties', {
      method: 'GET', credentials: 'include', headers: undefined, body: undefined,
    })
  })

  it('reads a property by its URL-encoded index', async () => {
    const listing = { idx: 'A/B', title: 'Sunny apartment' }
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, listing))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.readProperty('A/B')).resolves.toEqual(listing)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/properties/A%2FB', {
      method: 'GET', credentials: 'include', headers: undefined, body: undefined,
    })
  })

  it('registers a property as cookie-backed JSON', async () => {
    const property = { title: 'Sunny apartment', price_krw: 500000000 }
    const created = { idx: 12, ...property }
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(201, created))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.registerProperty(property)).resolves.toEqual(created)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/properties', {
      method: 'POST', credentials: 'include',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(property),
    })
  })
})

describe('question API methods', () => {
  it('creates, reads, updates, lists, and deletes public questions', async () => {
    const question = { id: 4, title: '창문 방향', contents: '남향인가요?', image_url: null, answer: null }
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(200, [question]))
      .mockResolvedValueOnce(makeResponse(201, question))
      .mockResolvedValueOnce(makeResponse(200, question))
      .mockResolvedValueOnce(makeResponse(200, question))
      .mockResolvedValueOnce(makeResponse(204, null))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.listQuestions()).resolves.toEqual([question])
    await expect(client.createQuestion({ title: question.title, contents: question.contents, image_url: null })).resolves.toEqual(question)
    await expect(client.readQuestion(4)).resolves.toEqual(question)
    await expect(client.updateQuestion(4, { title: '바뀐 제목', contents: '수정된 질문', image_url: null })).resolves.toEqual(question)
    await expect(client.deleteQuestion(4)).resolves.toBeNull()

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/questions',
      'http://localhost:8000/questions',
      'http://localhost:8000/questions/4',
      'http://localhost:8000/questions/4',
      'http://localhost:8000/questions/4',
    ])
    expect(fetchMock.mock.calls.map(([, options]) => options.method)).toEqual(['GET', 'POST', 'GET', 'PUT', 'DELETE'])
  })

  it('uploads one image to the presigned URL before returning its public URL', async () => {
    const file = new Blob(['image-bytes'], { type: 'image/png' })
    Object.defineProperty(file, 'name', { value: 'room.png' })
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(200, {
        upload_url: 'https://s3.example/upload?signature=abc',
        image_url: 'https://bucket.s3.ap-northeast-2.amazonaws.com/questions/id.png',
      }))
      .mockResolvedValueOnce({ ok: true, status: 200 })
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.uploadQuestionImage(file)).resolves.toBe('https://bucket.s3.ap-northeast-2.amazonaws.com/questions/id.png')
    expect(fetchMock).toHaveBeenNthCalledWith(1, 'http://localhost:8000/questions/presigned-upload', {
      method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: 'room.png', content_type: 'image/png' }),
    })
    expect(fetchMock).toHaveBeenNthCalledWith(2, 'https://s3.example/upload?signature=abc', {
      method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: file,
    })
  })

  it('does not return an image URL when direct upload fails', async () => {
    const file = new Blob(['image-bytes'], { type: 'image/jpeg' })
    Object.defineProperty(file, 'name', { value: 'room.jpg' })
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(200, { upload_url: 'https://s3.example/upload', image_url: 'https://s3.example/room.jpg' }))
      .mockResolvedValueOnce({ ok: false, status: 403 })
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.uploadQuestionImage(file)).rejects.toMatchObject({
      name: 'ApiError', status: 403, message: '이미지를 업로드하지 못했습니다. (403)',
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('creates or replaces one answer and supports deleting it', async () => {
    const answer = { id: 5, contents: '거실은 남향입니다.' }
    const question = { id: 4, title: '창문 방향', contents: '남향인가요?', image_url: null, answer }
    const fetchMock = jest.fn()
      .mockResolvedValueOnce(makeResponse(201, question))
      .mockResolvedValueOnce(makeResponse(200, question))
      .mockResolvedValueOnce(makeResponse(204, null))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.createQuestionAnswer(4, { contents: answer.contents })).resolves.toEqual(question)
    await expect(client.updateQuestionAnswer(4, { contents: '남향이에요.' })).resolves.toEqual(question)
    await expect(client.deleteQuestionAnswer(4)).resolves.toBeNull()
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      'http://localhost:8000/questions/4/answer',
      'http://localhost:8000/questions/4/answer',
      'http://localhost:8000/questions/4/answer',
    ])
    expect(fetchMock.mock.calls.map(([, options]) => options.method)).toEqual(['POST', 'PUT', 'DELETE'])
  })
})
