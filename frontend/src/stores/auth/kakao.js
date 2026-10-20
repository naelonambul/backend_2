export const KAKAO_UNAVAILABLE_MESSAGE = '카카오 로그인을 사용할 수 없습니다. 설정을 확인해 주세요.'
export const KAKAO_CALLBACK_INVALID_MESSAGE = '카카오 로그인 정보를 확인할 수 없습니다. 다시 시도해 주세요.'
export const KAKAO_CALLBACK_FAILED_MESSAGE = '카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.'

export async function beginKakaoLogin({ sdk, javascriptKey, redirectUri, api }) {
  if (!sdk || !javascriptKey || !redirectUri || !api) {
    throw new Error(KAKAO_UNAVAILABLE_MESSAGE)
  }

  if (!sdk.isInitialized()) sdk.init(javascriptKey)
  const { state } = await api.createKakaoState()
  if (!state) throw new Error(KAKAO_UNAVAILABLE_MESSAGE)
  sdk.Auth.authorize({ redirectUri, state })
}

export function getKakaoCallbackError(query = {}) {
  if (!query.error) return ''
  if (query.error === 'access_denied') return '카카오 로그인이 취소되었습니다.'
  return KAKAO_CALLBACK_FAILED_MESSAGE
}

export async function exchangeKakaoCode({ code, state, api }) {
  if (typeof code !== 'string' || !code || typeof state !== 'string' || !state) {
    throw new Error(KAKAO_CALLBACK_INVALID_MESSAGE)
  }
  await api.completeKakaoLogin({ code, state })
}
