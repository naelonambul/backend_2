import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path):
    database_path = (tmp_path / "test.db").as_posix()
    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(autoflush=False, bind=test_engine)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://www.nenene.n-e.kr") as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_signup_returns_public_user_fields_and_rejects_duplicates(client):
    payload = {"email": "reader@example.com", "password": "secret", "name": "독자"}

    response = client.post("/user/signup", json=payload)

    assert response.status_code == 200
    assert response.json() == {"email": "reader@example.com", "name": "독자"}
    assert "password" not in response.json()

    duplicate = client.post("/user/signup", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "이미 가입된 이메일입니다."


def test_login_returns_email_and_sets_http_only_cookie(client, monkeypatch):
    monkeypatch.setattr("app.api.routers.user.settings.DOMAIN", "nenene.n-e.kr")
    client.post(
        "/user/signup",
        json={"email": "reader@example.com", "password": "secret", "name": "독자"},
    )

    response = client.post(
        "/user/login", json={"email": "reader@example.com", "password": "secret"}
    )

    assert response.status_code == 200
    assert response.json() == {"email": "reader@example.com"}
    assert response.cookies.get("EN_AT")
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "domain=nenene.n-e.kr" in response.headers["set-cookie"].lower()


def test_login_rejects_unknown_users_and_incorrect_passwords(client):
    client.post(
        "/user/signup",
        json={"email": "reader@example.com", "password": "secret", "name": "독자"},
    )

    wrong_password = client.post(
        "/user/login", json={"email": "reader@example.com", "password": "wrong"}
    )
    unknown_user = client.post(
        "/user/login", json={"email": "missing@example.com", "password": "secret"}
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == "이메일 또는 비밀번호가 올바르지 않습니다."


def test_board_registration_can_be_read_by_returned_index(client):
    created = client.post(
        "/board/register",
        json={"title": "첫 번째 노트", "contents": "천천히 기록하기"},
    )

    assert created.status_code == 200
    assert created.json()["title"] == "첫 번째 노트"
    assert created.json()["contents"] == "천천히 기록하기"

    fetched = client.get(f"/board/read/{created.json()['idx']}")
    assert fetched.status_code == 200
    assert fetched.json() == created.json()


def test_board_list_returns_entries_in_descending_index_order(client):
    client.post("/board/register", json={"title": "첫 글", "contents": "먼저 작성"})
    client.post("/board/register", json={"title": "두 번째 글", "contents": "나중 작성"})

    response = client.get("/board/list")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["두 번째 글", "첫 글"]


def test_board_list_is_empty_when_there_are_no_entries(client):
    response = client.get("/board/list")

    assert response.status_code == 200
    assert response.json() == []


def test_reading_an_unknown_board_entry_returns_not_found(client):
    response = client.get("/board/read/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "노트를 찾을 수 없습니다."


def test_root_endpoint_reports_service_status(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "message" in response.json()
