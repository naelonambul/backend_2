import { ApiError, createApiClient, normalizeBaseUrl } from './api'

function makeResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  }
}

describe('note API client', () => {
  it('normalizes the configured server URL', () => {
    expect(normalizeBaseUrl('  http://localhost:8000///  ')).toBe('http://localhost:8000')
  })

  it('posts signup data as JSON and includes cookies', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, { email: 'moa@example.com', name: '모아' }))
    const client = createApiClient('http://localhost:8000/', fetchMock)

    const response = await client.signup({ email: 'moa@example.com', name: '모아', password: 'secret' })

    expect(response).toEqual({ email: 'moa@example.com', name: '모아' })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/user/signup', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'moa@example.com', name: '모아', password: 'secret' }),
    })
  })

  it('reads a board entry by its numeric index', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, { idx: 7, title: '첫 기록', contents: '내용' }))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.readBoard(7)).resolves.toEqual({ idx: 7, title: '첫 기록', contents: '내용' })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/board/read/7', {
      method: 'GET', credentials: 'include', headers: undefined, body: undefined,
    })
  })

  it('loads the board collection from the list endpoint', async () => {
    const rows = [{ idx: 3, title: '세 번째', contents: '최근 글' }, { idx: 2, title: '두 번째', contents: '이전 글' }]
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(200, rows))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.listBoards()).resolves.toEqual(rows)
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/board/list', {
      method: 'GET', credentials: 'include', headers: undefined, body: undefined,
    })
  })

  it('turns FastAPI validation errors into a readable message', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(422, { detail: [{ msg: 'Field required' }, { msg: 'Invalid email' }] }))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.ping()).rejects.toEqual(expect.objectContaining({
      name: 'ApiError', message: 'Field required, Invalid email', status: 422,
    }))
  })

  it('uses the HTTP status when FastAPI does not provide a detail', async () => {
    const fetchMock = jest.fn().mockResolvedValue(makeResponse(503, {}))
    const client = createApiClient('http://localhost:8000', fetchMock)

    await expect(client.login({ email: 'a@b.com', password: 'x' })).rejects.toBeInstanceOf(ApiError)
    await expect(client.login({ email: 'a@b.com', password: 'x' })).rejects.toMatchObject({
      message: '요청을 처리하지 못했습니다. (503)', status: 503,
    })
  })
})
