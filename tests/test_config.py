from app.core.config import Settings
from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient


def test_frontend_and_backend_origins_default_to_loopback_addresses(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    monkeypatch.delenv("BACKEND_ORIGIN", raising=False)

    settings = Settings(_env_file=None)

    assert settings.FRONTEND_ORIGIN == "http://127.0.0.1:5173"
    assert settings.BACKEND_ORIGIN == "http://127.0.0.1:8000"


def test_s3_settings_accept_bucket_and_region_without_static_credentials():
    settings = Settings(
        _env_file=None,
        AWS_REGION="ap-northeast-2",
        AWS_S3_BUCKET_NAME="questions-bucket",
    )

    assert settings.AWS_REGION == "ap-northeast-2"
    assert settings.AWS_S3_BUCKET_NAME == "questions-bucket"
    assert settings.AWS_ACCESS_KEY_ID == ""
    assert settings.AWS_SECRET_ACCESS_KEY == ""


def test_cors_allows_requests_from_the_configured_frontend_origin():
    response = TestClient(app).options(
        "/user/me",
        headers={
            "Origin": settings.FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.FRONTEND_ORIGIN


def test_cors_allows_preflight_from_production_frontend_origin():
    production_origin = "https://www.nenene.n-e.kr"
    response = TestClient(app).options(
        "/user/login",
        headers={
            "Origin": production_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == production_origin
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
