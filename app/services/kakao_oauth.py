from typing import Any

import httpx
from fastapi import Depends

from app.core.config import settings


class KakaoOAuthError(Exception):
    """Raised when Kakao cannot authenticate or return a usable profile."""


class KakaoOAuthService:
    TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    PROFILE_URL = "https://kapi.kakao.com/v2/user/me"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def fetch_profile(self, code: str) -> dict[str, str]:
        if not settings.KAKAO_REST_API_KEY.strip():
            raise KakaoOAuthError("Kakao REST API key is not configured")

        token_form = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "code": code,
        }
        if settings.KAKAO_CLIENT_SECRET:
            token_form["client_secret"] = settings.KAKAO_CLIENT_SECRET

        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=10.0) as client:
                token_response = await client.post(self.TOKEN_URL, data=token_form)
                token_response.raise_for_status()
                token_payload = token_response.json()
                if not isinstance(token_payload, dict):
                    raise KakaoOAuthError("Kakao returned an invalid token response")
                access_token = token_payload.get("access_token")
                if not isinstance(access_token, str) or not access_token:
                    raise KakaoOAuthError("Kakao returned no access token")

                profile_response = await client.get(
                    self.PROFILE_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                profile_response.raise_for_status()
                profile_payload: Any = profile_response.json()
        except KakaoOAuthError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise KakaoOAuthError("Kakao provider request failed") from exc

        provider_id = profile_payload.get("id") if isinstance(profile_payload, dict) else None
        if not isinstance(provider_id, (str, int)) or isinstance(provider_id, bool) or not str(provider_id):
            raise KakaoOAuthError("Kakao profile has no user id")

        account_info = profile_payload.get("kakao_account") or {}
        profile_info = account_info.get("profile") or {} if isinstance(account_info, dict) else {}
        nickname = profile_info.get("nickname") if isinstance(profile_info, dict) else None
        if not nickname:
            properties = profile_payload.get("properties") or {}
            nickname = properties.get("nickname") if isinstance(properties, dict) else None
        return {"id": str(provider_id), "nickname": str(nickname or "카카오 사용자")}


def get_kakao_oauth_service() -> KakaoOAuthService:
    return KakaoOAuthService()
