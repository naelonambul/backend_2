import { getCurrentUserOrNull } from '../stores/auth/session'

describe('login session helper', () => {
  it('returns the current profile when the session is valid', async () => {
    const profile = { name: '모아', email: 'moa@example.com', provider: 'email' }
    const api = { getCurrentUser: jest.fn().mockResolvedValue(profile) }

    await expect(getCurrentUserOrNull(api)).resolves.toEqual(profile)
  })

  it('treats an unauthorized session as signed out', async () => {
    const api = {
      getCurrentUser: jest.fn().mockRejectedValue(Object.assign(new Error('로그인이 필요합니다.'), { status: 401 })),
    }

    await expect(getCurrentUserOrNull(api)).resolves.toBeNull()
  })

  it('preserves errors when the session request fails for another reason', async () => {
    const api = { getCurrentUser: jest.fn().mockRejectedValue(new Error('네트워크 오류')) }

    await expect(getCurrentUserOrNull(api)).rejects.toThrow('네트워크 오류')
  })
})
