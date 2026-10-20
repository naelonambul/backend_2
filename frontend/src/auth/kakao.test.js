import { beginKakaoLogin, getKakaoCallbackError, exchangeKakaoCode } from './kakao'

describe('Kakao login helpers', () => {
  it('initializes the SDK, obtains a one-time state, then starts authorization', async () => {
    const sdk = {
      isInitialized: jest.fn(() => false),
      init: jest.fn(),
      Auth: { authorize: jest.fn() },
    }
    const api = { createKakaoState: jest.fn().mockResolvedValue({ state: 'csrf-state' }) }

    await beginKakaoLogin({
      sdk,
      javascriptKey: 'public-key',
      redirectUri: 'http://localhost:5173/auth/kakao/callback',
      api,
    })

    expect(sdk.init).toHaveBeenCalledWith('public-key')
    expect(api.createKakaoState).toHaveBeenCalledTimes(1)
    expect(sdk.Auth.authorize).toHaveBeenCalledWith({
      redirectUri: 'http://localhost:5173/auth/kakao/callback',
      state: 'csrf-state',
    })
  })

  it('reuses an already initialized SDK and reports a missing public key', async () => {
    const sdk = { isInitialized: jest.fn(() => true), init: jest.fn(), Auth: { authorize: jest.fn() } }
    const api = { createKakaoState: jest.fn().mockResolvedValue({ state: 'state' }) }

    await beginKakaoLogin({ sdk, javascriptKey: 'key', redirectUri: '/callback', api })
    expect(sdk.init).not.toHaveBeenCalled()
    await expect(beginKakaoLogin({ sdk, javascriptKey: '', redirectUri: '/callback', api }))
      .rejects.toThrow('카카오 로그인을 사용할 수 없습니다. 설정을 확인해 주세요.')
  })

  it('maps provider cancellation and provider errors to readable messages', () => {
    expect(getKakaoCallbackError({ error: 'access_denied' }))
      .toBe('카카오 로그인이 취소되었습니다.')
    expect(getKakaoCallbackError({ error: 'temporarily_unavailable' }))
      .toBe('카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.')
  })

  it('requires the callback code and state before exchanging them', async () => {
    const api = { completeKakaoLogin: jest.fn() }
    await expect(exchangeKakaoCode({ code: '', state: 'state', api }))
      .rejects.toThrow('카카오 로그인 정보를 확인할 수 없습니다. 다시 시도해 주세요.')
    await expect(exchangeKakaoCode({ code: 'code', state: 'state', api }))
      .resolves.toBeUndefined()
    expect(api.completeKakaoLogin).toHaveBeenCalledWith({ code: 'code', state: 'state' })
  })
})
