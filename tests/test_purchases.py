import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app


class FakePortOne:
    def __init__(self):
        self.payment = None
        self.lookup_error = None
        self.cancel_error = None
        self.cancel_response = {"cancellation": {"status": "SUCCEEDED"}}
        self.lookups = []
        self.cancellations = []

    def get_payment(self, payment_id):
        self.lookups.append(payment_id)
        if self.lookup_error:
            raise self.lookup_error
        return self.payment

    def cancel_payment(self, payment_id, reason):
        self.cancellations.append((payment_id, reason))
        if self.cancel_error:
            raise self.cancel_error
        return self.cancel_response


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = (tmp_path / "purchases.db").as_posix()
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

    purchase_router = importlib.import_module("app.api.routers.purchase")
    portone = FakePortOne()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[purchase_router.get_portone_client] = lambda: portone
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_EMAIL", "seller@example.com")
    monkeypatch.setitem(settings.__dict__, "PROPERTY_SELLER_SECRET", "secret")
    monkeypatch.setitem(settings.__dict__, "PORTONE_API_SECRET", "portone-test-secret")
    with TestClient(app) as test_client:
        test_client.portone = portone
        test_client.db_factory = test_session
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def signup(client, email, password="buyer-password"):
    response = client.post(
        "/user/signup", json={"email": email, "password": password, "name": email}
    )
    assert response.status_code == 200, response.text


def login(client, email, password="buyer-password"):
    response = client.post("/user/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def property_payload(price=100_000):
    return {
        "title": "Seoul apartment",
        "address": "Seoul",
        "price_krw": price,
        "area_m2": 55,
        "room_count": 2,
        "description": "A home",
        "image_url": None,
    }


def create_property(client, price=100_000):
    signup(client, "seller@example.com", "secret")
    login(client, "seller@example.com", "secret")
    response = client.post("/properties", json=property_payload(price))
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return response.json()


def create_purchase(client, property_idx, email="buyer@example.com"):
    signup(client, email)
    login(client, email)
    response = client.post(f"/properties/{property_idx}/purchases")
    return response


def purchase_record(client, purchase_id):
    Purchase = importlib.import_module("app.models.purchase").Purchase
    with client.db_factory() as db:
        return db.scalar(select(Purchase).where(Purchase.purchase_id == purchase_id))


def payment_for(order, *, status="PAID", total=None, currency="KRW", payment_id=None):
    return {
        "id": payment_id or order["payment_id"],
        "status": status,
        "amount": {"total": total if total is not None else order["amount" if "amount" in order else "amount_krw"]},
        "currency": currency,
    }


def test_purchase_requires_login(client):
    property_item = create_property(client)

    response = client.post(f"/properties/{property_item['idx']}/purchases")

    assert response.status_code == 401


def test_buyer_creates_pending_purchase_using_database_price(client):
    property_item = create_property(client, 137_500)

    response = create_purchase(client, property_item["idx"])

    assert response.status_code == 200
    order = response.json()
    assert order["amount"] == 137_500
    assert order["currency"] == "KRW"
    assert datetime.fromisoformat(order["expires_at"].replace("Z", "+00:00")).utcoffset() is not None
    assert order["order_name"] == "Seoul apartment"
    assert client.get(f"/properties/{property_item['idx']}").json()["availability"] == "reserved"
    assert client.get("/properties").json()[0]["availability"] == "reserved"
    assert purchase_record(client, order["purchase_id"]).amount_krw == 137_500
    assert purchase_record(client, order["purchase_id"]).status == "pending"


def test_seller_and_self_purchase_are_forbidden(client):
    property_item = create_property(client)
    login(client, "seller@example.com", "secret")

    response = client.post(f"/properties/{property_item['idx']}/purchases")

    assert response.status_code == 403


def test_only_one_active_purchase_exists_per_property(client):
    property_item = create_property(client)
    first = create_purchase(client, property_item["idx"])
    assert first.status_code == 200
    client.cookies.clear()

    second = create_purchase(client, property_item["idx"], "second@example.com")

    assert second.status_code == 409


def test_expired_pending_purchase_releases_property(client):
    property_item = create_property(client)
    first = create_purchase(client, property_item["idx"])
    client.cookies.clear()
    Purchase = importlib.import_module("app.models.purchase").Purchase
    with client.db_factory() as db:
        old = db.scalar(select(Purchase).where(Purchase.purchase_id == first.json()["purchase_id"]))
        old.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    assert client.get(f"/properties/{property_item['idx']}").json()["availability"] == "available"
    assert client.get("/properties").json()[0]["availability"] == "available"

    second = create_purchase(client, property_item["idx"], "second@example.com")

    assert second.status_code == 200
    assert purchase_record(client, first.json()["purchase_id"]).status == "cancelled"


@pytest.mark.parametrize("reported_status", ["FAILED", "CANCELLED"])
def test_mismatched_portone_payment_id_does_not_change_terminal_payment_state(
    client, reported_status
):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.portone.payment = payment_for(
        order, status=reported_status, payment_id="different-payment-id"
    )
    client.cookies.clear()
    login(client, "buyer@example.com")

    response = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )

    assert response.status_code == 502
    assert purchase_record(client, order["purchase_id"]).status == "pending"
    assert client.get(f"/properties/{property_item['idx']}").json()["availability"] == "reserved"


def test_zero_price_property_cannot_be_purchased(client):
    property_item = create_property(client, 0)
    response = create_purchase(client, property_item["idx"])

    assert response.status_code == 422


def test_purchase_returns_503_when_portone_secret_is_missing(client, monkeypatch):
    property_item = create_property(client)
    purchase_router = importlib.import_module("app.api.routers.purchase")
    app.dependency_overrides.pop(purchase_router.get_portone_client, None)
    monkeypatch.setitem(settings.__dict__, "PORTONE_API_SECRET", " ")
    signup(client, "buyer@example.com")
    login(client, "buyer@example.com")

    response = client.post(f"/properties/{property_item['idx']}/purchases")

    assert response.status_code == 503
    Purchase = importlib.import_module("app.models.purchase").Purchase
    with client.db_factory() as db:
        assert db.scalars(select(Purchase)).all() == []


def test_confirmation_requires_order_owner_and_matching_payment_id(client):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.cookies.clear()
    signup(client, "other@example.com")
    login(client, "other@example.com")
    denied = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )
    assert denied.status_code == 403
    client.cookies.clear()
    login(client, "buyer@example.com")
    mismatch = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": "wrong-payment-id"}
    )
    assert mismatch.status_code == 400
    assert purchase_record(client, order["purchase_id"]).status == "pending"
    assert client.portone.lookups == []


@pytest.mark.parametrize(
    ("payment_status", "total", "currency", "expected_status", "cancel_count"),
    [
        ("PAID", 99_999, "KRW", "failed", 1),
        ("PAID", 100_000, "USD", "failed", 1),
        ("READY", 100_000, "KRW", "pending", 0),
    ],
)
def test_paid_confirmation_requires_exact_amount_currency_and_paid_status(
    client, payment_status, total, currency, expected_status, cancel_count
):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.portone.payment = payment_for(order, status=payment_status, total=total, currency=currency)
    client.cookies.clear()
    login(client, "buyer@example.com")

    response = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )

    assert response.status_code == 200
    assert purchase_record(client, order["purchase_id"]).status == expected_status
    assert len(client.portone.cancellations) == cancel_count


def test_terminal_unsuccessful_payment_releases_reservation(client):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.portone.payment = payment_for(order, status="FAILED")
    client.cookies.clear()
    login(client, "buyer@example.com")

    response = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )
    assert response.json()["status"] == "failed"
    client.cookies.clear()
    second = create_purchase(client, property_item["idx"], "second@example.com")

    assert second.status_code == 200


def test_portone_lookup_timeout_keeps_order_pending(client):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.portone.lookup_error = importlib.import_module("app.services.portone").PortOneError(
        "retry", retryable=True
    )
    client.cookies.clear()
    login(client, "buyer@example.com")

    response = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )

    assert response.status_code == 503
    assert purchase_record(client, order["purchase_id"]).status == "pending"


def test_paid_confirmation_is_idempotent(client):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    client.portone.payment = payment_for(order)
    client.cookies.clear()
    login(client, "buyer@example.com")
    path = f"/purchases/{order['purchase_id']}/confirm"

    first = client.post(path, json={"payment_id": order["payment_id"]})
    second = client.post(path, json={"payment_id": order["payment_id"]})

    assert first.json()["status"] == "paid"
    assert second.json()["status"] == "paid"
    assert client.get(f"/properties/{property_item['idx']}").json()["availability"] == "sold"
    assert client.get("/properties").json()[0]["availability"] == "sold"
    assert len(client.portone.lookups) == 1


@pytest.mark.parametrize("cancel_fails", [False, True])
def test_late_paid_order_is_cancelled_or_kept_refund_pending(client, cancel_fails):
    property_item = create_property(client)
    order_response = create_purchase(client, property_item["idx"])
    order = order_response.json()
    Purchase = importlib.import_module("app.models.purchase").Purchase
    with client.db_factory() as db:
        record = db.scalar(select(Purchase).where(Purchase.purchase_id == order["purchase_id"]))
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    client.portone.payment = payment_for(order)
    if cancel_fails:
        client.portone.cancel_error = importlib.import_module("app.services.portone").PortOneError(
            "cancel failed", retryable=True
        )
    client.cookies.clear()
    login(client, "buyer@example.com")

    response = client.post(
        f"/purchases/{order['purchase_id']}/confirm", json={"payment_id": order["payment_id"]}
    )

    assert response.status_code == 200
    assert response.json()["status"] == ("refund_pending" if cancel_fails else "cancelled")
    assert client.portone.cancellations == [(order["payment_id"], "Late or conflicting payment")]


@pytest.mark.parametrize("competing_status", ["pending", "paid"])
def test_conflicting_late_paid_capture_does_not_cancel_competing_buyer_order(
    client, competing_status
):
    property_item = create_property(client)
    stale_response = create_purchase(client, property_item["idx"], "stale-buyer@example.com")
    stale_order = stale_response.json()
    Purchase = importlib.import_module("app.models.purchase").Purchase
    with client.db_factory() as db:
        stale = db.scalar(
            select(Purchase).where(Purchase.purchase_id == stale_order["purchase_id"])
        )
        stale.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    competing_response = create_purchase(client, property_item["idx"], "current-buyer@example.com")
    assert competing_response.status_code == 200
    competing_order = competing_response.json()
    if competing_status == "paid":
        with client.db_factory() as db:
            current = db.scalar(
                select(Purchase).where(Purchase.purchase_id == competing_order["purchase_id"])
            )
            current.status = "paid"
            current.paid_at = datetime.now(timezone.utc)
            db.commit()
    client.portone.payment = payment_for(stale_order)
    client.portone.cancel_error = importlib.import_module("app.services.portone").PortOneError(
        "cancel failed", retryable=True
    )
    client.cookies.clear()
    login(client, "stale-buyer@example.com")

    response = client.post(
        f"/purchases/{stale_order['purchase_id']}/confirm",
        json={"payment_id": stale_order["payment_id"]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "refund_pending"
    assert purchase_record(client, competing_order["purchase_id"]).status == competing_status
    assert purchase_record(client, stale_order["purchase_id"]).status == "cancelled"
    Reconciliation = importlib.import_module("app.models.payment_reconciliation").PaymentReconciliation
    with client.db_factory() as db:
        recovery = db.get(Reconciliation, stale_order["purchase_id"])
        assert recovery is not None
        assert recovery.payment_id == stale_order["payment_id"]
        assert recovery.status == "refund_pending"
        active = db.scalars(
            select(Purchase).where(
                Purchase.property_idx == property_item["idx"],
                Purchase.status.in_(("pending", "paid", "refund_pending")),
            )
        ).all()
        assert [order.purchase_id for order in active] == [competing_order["purchase_id"]]

    client.portone.cancel_error = None
    response = client.post(
        f"/purchases/{stale_order['purchase_id']}/confirm",
        json={"payment_id": stale_order["payment_id"]},
    )
    assert response.json()["status"] == "cancelled"
    with client.db_factory() as db:
        assert db.get(Reconciliation, stale_order["purchase_id"]) is None
    assert purchase_record(client, competing_order["purchase_id"]).status == competing_status
