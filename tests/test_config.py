from app.core.config import Settings
from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient


def test_settings_default_to_dotenv_instead_of_dotenv_remote(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("DB_HOST", "DB_READ_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(
        "DB_HOST=local-db\nDB_READ_HOST=local-read-db\nDB_USER=local-user\nDB_PASSWORD=local-password\nDB_NAME=web\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.remote").write_text(
        "DB_HOST=remote-db\nDB_READ_HOST=remote-read-db\nDB_USER=remote-user\nDB_PASSWORD=remote-password\nDB_NAME=web\n",
        encoding="utf-8",
    )

    local_settings = Settings()

    assert local_settings.database_url.host == "local-db"
    assert local_settings.read_database_url.host == "local-read-db"
    assert local_settings.database_url.username == "local-user"
    assert local_settings.database_url.password == "local-password"


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


def test_database_settings_build_mariadb_url_from_separate_values():
    database_settings = Settings(
        _env_file=None,
        DB_HOST="100.100.100.200",
        DB_READ_HOST="100.100.100.201",
        DB_PORT=3306,
        DB_USER="admin",
        DB_PASSWORD="p@ss:/word",
        DB_NAME="web",
    )

    url = database_settings.database_url

    assert url.drivername == "mysql+pymysql"
    assert url.host == "100.100.100.200"
    assert url.port == 3306
    assert url.username == "admin"
    assert url.password == "p@ss:/word"
    assert url.database == "web"
    assert database_settings.read_database_url.host == "100.100.100.201"


def test_database_url_uses_configured_url_when_no_database_host_is_set():
    database_settings = Settings(_env_file=None, DATABASE_URL="sqlite:///custom.db")

    assert str(database_settings.database_url) == "sqlite:///custom.db"
    assert database_settings.read_database_url == database_settings.database_url


def test_read_database_url_uses_replica_host_with_a_full_database_url():
    database_settings = Settings(
        _env_file=None,
        DATABASE_URL="mysql+pymysql://admin:secret@100.100.100.245:3307/web?charset=utf8mb4",
        DB_READ_HOST="100.100.100.246",
    )

    read_url = database_settings.read_database_url

    assert read_url.host == "100.100.100.246"
    assert read_url.port == 3307
    assert read_url.username == "admin"
    assert read_url.password == "secret"
    assert read_url.database == "web"


def test_database_url_defaults_to_local_sqlite():
    database_settings = Settings(_env_file=None)

    assert str(database_settings.database_url) == "sqlite:///app.db"


def test_app_database_settings_are_isolated_from_repository_dotenv():
    assert settings.DB_HOST == ""
    assert settings.DB_READ_HOST == ""
    assert str(settings.database_url).startswith("sqlite:")


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
