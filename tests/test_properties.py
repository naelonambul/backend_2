import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = (tmp_path / "properties.db").as_posix()
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
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_EMAIL", "seller@example.com")
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "secret")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def signup_and_login(client, email, name="Account"):
    client.post("/user/signup", json={"email": email, "password": "secret", "name": name})
    return client.post("/user/login", json={"email": email, "password": "secret"})


def listing(title="Listing", **overrides):
    payload = {
        "title": title,
        "address": "Seoul",
        "price_krw": 100000000,
        "area_m2": 42.5,
        "room_count": 2,
        "description": "A comfortable home",
        "image_url": None,
    }
    payload.update(overrides)
    return payload


def test_property_list_is_empty_then_returns_newest_first(client):
    assert client.get("/properties").json() == []
    signup_and_login(client, "seller@example.com")
    client.post("/properties", json=listing("First"))
    client.post("/properties", json=listing("Second"))

    response = client.get("/properties")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Second", "First"]
    assert [item["availability"] for item in response.json()] == ["available", "available"]


def test_property_detail_returns_listing_and_unknown_returns_404(client):
    signup_and_login(client, "seller@example.com")
    created = client.post("/properties", json=listing())

    assert created.status_code == 200
    assert client.get(f"/properties/{created.json()['idx']}").json() == created.json()
    assert created.json()["availability"] == "available"
    assert client.get("/properties/999").status_code == 404


def test_configured_seller_can_create_persistent_property(client):
    signup_and_login(client, "seller@example.com")

    response = client.post("/properties", json=listing())

    assert response.status_code == 200
    assert response.json()["title"] == "Listing"
    assert "seller_user_idx" not in response.json()
    assert client.get(f"/properties/{response.json()['idx']}").json() == response.json()


def test_buyer_and_unauthenticated_users_cannot_create_properties(client):
    assert client.post("/properties", json=listing()).status_code == 401
    client.cookies.set("EN_AT", "invalid-session-token")
    assert client.post("/properties", json=listing()).status_code == 401
    client.cookies.clear()
    signup_and_login(client, "buyer@example.com")
    assert client.post("/properties", json=listing()).status_code == 403


def test_unset_seller_email_denies_property_creation(client, monkeypatch):
    signup_and_login(client, "seller@example.com")
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_EMAIL", "  ")

    assert client.post("/properties", json=listing()).status_code == 403


def test_seller_matching_ignores_email_case_and_outer_whitespace(client, monkeypatch):
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_EMAIL", "  SELLER@EXAMPLE.COM  ")
    signup_and_login(client, "seller@example.com")

    assert client.post("/properties", json=listing()).status_code == 200


def test_current_user_includes_configured_role(client):
    signup_and_login(client, "seller@example.com", "Seller")
    seller = client.get("/user/me")
    assert seller.status_code == 200
    assert seller.json() == {
        "name": "Seller", "email": "seller@example.com", "provider": "email", "role": "seller"
    }

    signup_and_login(client, "buyer@example.com", "Buyer")
    assert client.get("/user/me").json()["role"] == "buyer"


def test_seller_signup_requires_configured_secret_and_exact_password(client):
    wrong_password = client.post(
        "/user/signup",
        json={"email": "seller@example.com", "password": "wrong", "name": "Seller"},
    )
    assert wrong_password.status_code == 403

    accepted = client.post(
        "/user/signup",
        json={"email": "seller@example.com", "password": "secret", "name": "Seller"},
    )
    assert accepted.status_code == 200
    assert "password" not in accepted.json()
    assert client.post(
        "/user/login", json={"email": "seller@example.com", "password": "secret"}
    ).status_code == 200
    assert client.get("/user/me").json()["role"] == "seller"


def test_seller_signup_deduplicates_case_variants_and_login_resolves_them(client):
    created = client.post(
        "/user/signup",
        json={"email": "SELLER@EXAMPLE.COM", "password": "secret", "name": "Seller"},
    )
    assert created.status_code == 200
    assert created.json()["email"] == "seller@example.com"

    duplicate = client.post(
        "/user/signup",
        json={"email": "Seller@Example.com", "password": "secret", "name": "Second"},
    )
    assert duplicate.status_code == 400

    login = client.post(
        "/user/login", json={"email": " SELLER@EXAMPLE.COM ", "password": "secret"}
    )
    assert login.status_code == 200
    assert client.get("/user/me").json()["email"] == "seller@example.com"


def test_seller_signup_is_rejected_when_configured_secret_is_missing(client, monkeypatch):
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "  ")

    rejected = client.post(
        "/user/signup",
        json={"email": "seller@example.com", "password": "secret", "name": "Seller"},
    )
    assert rejected.status_code == 403

    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "secret")
    accepted = client.post(
        "/user/signup",
        json={"email": "seller@example.com", "password": "secret", "name": "Seller"},
    )
    assert accepted.status_code == 200


def test_buyer_signup_does_not_need_seller_secret(client, monkeypatch):
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "")
    signup = client.post(
        "/user/signup",
        json={"email": "buyer@example.com", "password": "buyer-password", "name": "Buyer"},
    )

    assert signup.status_code == 200
    assert client.post(
        "/user/login", json={"email": "buyer@example.com", "password": "buyer-password"}
    ).status_code == 200
    assert client.get("/user/me").json()["role"] == "buyer"


def test_seller_login_rejects_old_password_after_secret_changes(client, monkeypatch):
    client.post(
        "/user/signup",
        json={"email": "seller@example.com", "password": "secret", "name": "Seller"},
    )
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "rotated-secret")

    assert client.post(
        "/user/login", json={"email": "seller@example.com", "password": "secret"}
    ).status_code == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"title": ""}, {"title": "x" * 201}, {"address": ""},
        {"address": "x" * 301}, {"price_krw": -1}, {"price_krw": "invalid"},
        {"area_m2": 0}, {"area_m2": -1}, {"area_m2": "invalid"},
        {"room_count": -1}, {"room_count": "invalid"},
        {"description": ""}, {"description": "x" * 5001},
        {"image_url": "javascript:alert(1)"},
    ],
)
def test_invalid_property_values_are_rejected(client, changes):
    signup_and_login(client, "seller@example.com")

    assert client.post("/properties", json=listing(**changes)).status_code == 422


def test_zero_price_and_room_count_are_allowed(client):
    signup_and_login(client, "seller@example.com")

    response = client.post("/properties", json=listing(price_krw=0, room_count=0))

    assert response.status_code == 200
    assert response.json()["price_krw"] == 0
    assert response.json()["room_count"] == 0


def test_text_fields_accept_their_exact_maximum_lengths(client):
    signup_and_login(client, "seller@example.com")

    response = client.post(
        "/properties",
        json=listing(title="t" * 200, address="a" * 300, description="d" * 5000),
    )

    assert response.status_code == 200
    assert len(response.json()["title"]) == 200
    assert len(response.json()["address"]) == 300
    assert len(response.json()["description"]) == 5000
