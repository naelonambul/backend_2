import asyncio
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app
from app.models.social_account import SocialAccount
from app.models.user import User
from app.services.kakao_oauth import KakaoOAuthError, KakaoOAuthService, get_kakao_oauth_service


class FakeKakaoOAuthService:
    def __init__(self):
        self.profile = {"id": "kakao-123", "nickname": "하늘"}
        self.calls = []
        self.error = None

    async def fetch_profile(self, code):
        self.calls.append(code)
        if self.error:
            raise self.error
        return self.profile


@pytest.fixture
def client(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{(tmp_path / 'social-test.db').as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(autoflush=False, bind=test_engine)
    oauth = FakeKakaoOAuthService()

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_kakao_oauth_service] = lambda: oauth
    app.state.test_session = test_session
    with TestClient(app, base_url="http://www.nenene.n-e.kr") as test_client:
        test_client.oauth = oauth
        yield test_client

    app.dependency_overrides.clear()
    del app.state.test_session
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def start_callback(client):
    state_response = client.post("/user/kakao/state")
    assert state_response.status_code == 200
    return state_response.json()["state"]


def test_kakao_state_is_random_and_stored_in_http_only_cookie(client):
    first = client.post("/user/kakao/state")
    first_state = first.json()["state"]
    client.cookies.clear()
    second = client.post("/user/kakao/state")

    assert first.status_code == second.status_code == 200
    assert first_state != second.json()["state"]
    assert "httponly" in first.headers["set-cookie"].lower()
    assert "max-age=300" in first.headers["set-cookie"].lower()


def test_kakao_callback_rejects_invalid_state_without_creating_account(client):
    start_callback(client)

    response = client.post("/user/kakao/callback", json={"code": "one-time-code", "state": "wrong"})

    with app.state.test_session() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(SocialAccount)) == 0
    assert response.status_code == 400
    assert response.headers.get("set-cookie", "").startswith('KAKAO_OAUTH_STATE="";')
    assert "max-age=0" in response.headers.get("set-cookie", "").lower()
    assert client.oauth.calls == []
    assert "EN_AT" not in response.cookies


def test_kakao_callback_rejects_non_ascii_state(client):
    start_callback(client)

    response = client.post("/user/kakao/callback", json={"code": "one-time-code", "state": "상태"})

    assert response.status_code == 400
    assert client.oauth.calls == []


def test_first_kakao_login_creates_social_user_and_http_only_session(client, monkeypatch):
    monkeypatch.setattr("app.api.routers.user.settings.DOMAIN", "nenene.n-e.kr")
    state = start_callback(client)

    response = client.post("/user/kakao/callback", json={"code": "one-time-code", "state": state})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "domain=nenene.n-e.kr" in response.headers["set-cookie"].lower()
    with app.state.test_session() as db:
        user = db.scalar(select(User))
        account = db.scalar(select(SocialAccount))
        assert user.name == "하늘"
        assert user.email is None and user.password is None
        assert account.provider == "kakao"
        assert account.provider_user_id == "kakao-123"
        assert account.user_idx == user.idx
        claims = jwt.decode(response.cookies["EN_AT"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert claims["sub"] == str(user.idx)


def test_returning_kakao_login_reuses_existing_user(client):
    state = start_callback(client)
    first = client.post("/user/kakao/callback", json={"code": "first-code", "state": state})
    client.cookies.clear()
    state = start_callback(client)
    second = client.post("/user/kakao/callback", json={"code": "second-code", "state": state})

    with app.state.test_session() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(SocialAccount)) == 1
    assert first.status_code == second.status_code == 200
    assert client.oauth.calls == ["first-code", "second-code"]


def test_password_login_still_works_and_uses_internal_user_id_for_session(client):
    client.post(
        "/user/signup",
        json={"email": "reader@example.com", "password": "secret", "name": "독자"},
    )

    response = client.post("/user/login", json={"email": "reader@example.com", "password": "secret"})
    claims = jwt.decode(response.cookies["EN_AT"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert response.status_code == 200
    assert claims["sub"] == "1"


def test_current_user_returns_password_account_profile(client):
    client.post(
        "/user/signup",
        json={"email": "reader@example.com", "password": "secret", "name": "Reader"},
    )
    client.post("/user/login", json={"email": "reader@example.com", "password": "secret"})

    response = client.get("/user/me")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Reader",
        "email": "reader@example.com",
        "provider": "email",
        "role": "buyer",
    }


def test_current_user_returns_kakao_account_profile(client):
    state = start_callback(client)
    client.post("/user/kakao/callback", json={"code": "one-time-code", "state": state})

    response = client.get("/user/me")

    assert response.status_code == 200
    assert response.json() == {
        "name": client.oauth.profile["nickname"],
        "email": None,
        "provider": "kakao",
        "role": "buyer",
    }


def test_current_user_rejects_missing_or_invalid_session(client):
    missing = client.get("/user/me")
    client.cookies.set("EN_AT", "not-a-jwt")

    invalid = client.get("/user/me")

    assert missing.status_code == 401
    assert invalid.status_code == 401


def test_logout_clears_session_cookie_and_current_user(client, monkeypatch):
    monkeypatch.setattr("app.api.routers.user.settings.DOMAIN", "nenene.n-e.kr")
    client.post(
        "/user/signup",
        json={"email": "reader@example.com", "password": "secret", "name": "Reader"},
    )
    client.post("/user/login", json={"email": "reader@example.com", "password": "secret"})

    response = client.post("/user/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert "domain=nenene.n-e.kr" in response.headers["set-cookie"].lower()
    assert client.get("/user/me").status_code == 401


def test_kakao_provider_failure_does_not_create_user_or_set_session(client):
    client.oauth.error = KakaoOAuthError("provider unavailable")
    state = start_callback(client)

    response = client.post("/user/kakao/callback", json={"code": "one-time-code", "state": state})

    with app.state.test_session() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
    assert response.status_code == 502
    assert response.json()["detail"] == "카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요."
    assert response.headers.get("set-cookie", "").startswith('KAKAO_OAUTH_STATE="";')
    assert "max-age=0" in response.headers.get("set-cookie", "").lower()
    assert "EN_AT" not in response.cookies


def test_kakao_oauth_service_exchanges_code_and_requests_only_profile(monkeypatch):
    monkeypatch.setattr(settings, "KAKAO_REST_API_KEY", "rest-key")
    monkeypatch.setattr(settings, "KAKAO_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "KAKAO_REDIRECT_URI", "http://127.0.0.1:5173/auth/kakao/callback")
    seen = []

    async def handler(request):
        seen.append(request)
        if request.method == "POST":
            assert request.url == KakaoOAuthService.TOKEN_URL
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["authorization_code"],
                "client_id": ["rest-key"],
                "client_secret": ["client-secret"],
                "redirect_uri": ["http://127.0.0.1:5173/auth/kakao/callback"],
                "code": ["one-time-code"],
            }
            return httpx.Response(200, json={"access_token": "provider-token"})

        assert request.url == KakaoOAuthService.PROFILE_URL
        assert request.headers["Authorization"] == "Bearer provider-token"
        return httpx.Response(200, json={
            "id": 456,
            "kakao_account": {"profile": {"nickname": "하늘"}},
        })

    service = KakaoOAuthService(transport=httpx.MockTransport(handler))
    profile = asyncio.run(service.fetch_profile("one-time-code"))

    assert profile == {"id": "456", "nickname": "하늘"}
    assert [request.method for request in seen] == ["POST", "GET"]
