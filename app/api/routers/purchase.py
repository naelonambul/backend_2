from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, is_configured_seller
from app.core.config import settings
from app.db.database import get_db
from app.models.property import Property
from app.models.purchase import Purchase, utc_now
from app.models.payment_reconciliation import PaymentReconciliation
from app.models.user import User
from app.schemas.purchase import (
    PurchaseConfirmRequest,
    PurchaseConfirmResponse,
    PurchaseCreateResponse,
)
from app.services.portone import PortOneClient, PortOneError

router = APIRouter(tags=["purchases"])
PENDING_LIFETIME = timedelta(minutes=15)


def get_portone_client() -> PortOneClient:
    secret = settings.PORTONE_API_SECRET
    if not secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment verification is not configured",
        )
    return PortOneClient(secret)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _confirm_response(purchase: Purchase, db: Session):
    unresolved = db.get(PaymentReconciliation, purchase.purchase_id) is not None
    return {
        "purchase_id": purchase.purchase_id,
        "status": "refund_pending" if unresolved else purchase.status,
    }


@router.post(
    "/properties/{property_idx}/purchases",
    response_model=PurchaseCreateResponse,
)
def create_purchase(
    property_idx: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _portone: PortOneClient = Depends(get_portone_client),
):
    property_record = db.get(Property, property_idx)
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if is_configured_seller(user.email) or property_record.seller_user_idx == user.idx:
        raise HTTPException(status_code=403, detail="Seller cannot purchase this property")
    if property_record.price_krw <= 0:
        raise HTTPException(status_code=422, detail="Property price must be positive")

    now = utc_now()
    try:
        expired = db.scalars(
            select(Purchase).where(
                Purchase.property_idx == property_idx,
                Purchase.status == "pending",
                Purchase.expires_at <= now,
            )
        ).all()
        for old_order in expired:
            old_order.status = "cancelled"
            old_order.updated_at = now
        db.flush()

        active = db.scalar(
            select(Purchase).where(
                Purchase.property_idx == property_idx,
                (
                    Purchase.status.in_(("paid", "refund_pending"))
                    | ((Purchase.status == "pending") & (Purchase.expires_at > now))
                ),
            )
        )
        unresolved_reconciliation = db.scalar(
            select(PaymentReconciliation.purchase_id)
            .join(Purchase, Purchase.purchase_id == PaymentReconciliation.purchase_id)
            .where(Purchase.property_idx == property_idx)
        )
        if active or unresolved_reconciliation:
            raise HTTPException(status_code=409, detail="Property is already reserved or sold")

        order = Purchase(
            purchase_id=str(uuid.uuid4()),
            payment_id=str(uuid.uuid4()),
            property_idx=property_record.idx,
            buyer_user_idx=user.idx,
            amount_krw=property_record.price_krw,
            currency="KRW",
            status="pending",
            created_at=now,
            updated_at=now,
            expires_at=now + PENDING_LIFETIME,
        )
        expires_at = order.expires_at
        db.add(order)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Property is already reserved or sold") from exc
    except Exception:
        db.rollback()
        raise

    return {
        "purchase_id": order.purchase_id,
        "payment_id": order.payment_id,
        "order_name": property_record.title,
        "amount": order.amount_krw,
        "currency": order.currency,
        "expires_at": expires_at,
    }


@router.post(
    "/purchases/{purchase_id}/confirm",
    response_model=PurchaseConfirmResponse,
)
def confirm_purchase(
    purchase_id: str,
    request: PurchaseConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    portone: PortOneClient = Depends(get_portone_client),
):
    order = db.get(Purchase, purchase_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    if order.buyer_user_idx != user.idx:
        raise HTTPException(status_code=403, detail="Purchase belongs to another user")
    if request.payment_id != order.payment_id:
        raise HTTPException(status_code=400, detail="Payment ID does not match purchase")
    if order.status == "paid":
        return _confirm_response(order, db)

    try:
        payment = portone.get_payment(order.payment_id)
    except PortOneError as exc:
        raise HTTPException(
            status_code=503 if exc.retryable else 502,
            detail="Payment status could not be verified",
        ) from exc

    payment_status = str(payment.get("status", "")).upper()
    if payment.get("id") != order.payment_id:
        raise HTTPException(status_code=502, detail="Payment identity could not be verified")
    reconciliation = db.get(PaymentReconciliation, order.purchase_id)
    expired_pending = (
        order.status == "pending" and _as_utc(order.expires_at) <= utc_now()
    )
    if expired_pending and payment_status != "PAID":
        if reconciliation:
            db.delete(reconciliation)
        order.status = "cancelled"
        order.updated_at = utc_now()
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=503, detail="Expired purchase could not be finalized"
            ) from exc
        return _confirm_response(order, db)
    if payment_status in {"FAILED", "CANCELLED"}:
        if reconciliation:
            db.delete(reconciliation)
        order.status = (
            "cancelled"
            if expired_pending or payment_status == "CANCELLED"
            else "failed"
        )
        order.updated_at = utc_now()
        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=503, detail="Payment result could not be persisted"
            ) from exc
        return _confirm_response(order, db)
    if payment_status != "PAID":
        return _confirm_response(order, db)

    amount = payment.get("amount")
    valid_payment = (
        isinstance(amount, dict)
        and type(amount.get("total")) is int
        and amount.get("total") == order.amount_krw
        and payment.get("currency") == order.currency
    )
    now = utc_now()
    unexpired = _as_utc(order.expires_at) > now
    competing = db.scalar(
        select(Purchase).where(
            Purchase.property_idx == order.property_idx,
            Purchase.purchase_id != order.purchase_id,
            (
                Purchase.status.in_(("paid", "refund_pending"))
                | ((Purchase.status == "pending") & (Purchase.expires_at > now))
            ),
        )
    )
    if valid_payment and unexpired and order.status == "pending" and not competing:
        order.status = "paid"
        order.paid_at = now
        order.updated_at = now
        try:
            db.commit()
            return _confirm_response(order, db)
        except SQLAlchemyError:
            # A reservation may have been created after the availability query.
            # Never report a terminal payment state until the database transition
            # commits; reload and reconcile the externally captured payment.
            db.rollback()
            try:
                db.expire_all()
                order = db.get(Purchase, purchase_id)
                if order is None:
                    raise HTTPException(
                        status_code=503, detail="Payment reconciliation is unavailable"
                    )
                reconciliation = db.get(PaymentReconciliation, order.purchase_id)
                now = utc_now()
                unexpired = _as_utc(order.expires_at) > now
                competing = db.scalar(
                    select(Purchase).where(
                        Purchase.property_idx == order.property_idx,
                        Purchase.purchase_id != order.purchase_id,
                        (
                            Purchase.status.in_(("paid", "refund_pending"))
                            | ((Purchase.status == "pending") & (Purchase.expires_at > now))
                        ),
                    )
                )
            except HTTPException:
                raise
            except SQLAlchemyError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=503, detail="Payment reconciliation is unavailable"
                ) from exc

    try:
        cancellation = portone.cancel_payment(order.payment_id, "Late or conflicting payment")
        if cancellation.get("cancellation", {}).get("status") != "SUCCEEDED":
            raise PortOneError("Payment cancellation is not complete", retryable=True)
        order.status = "cancelled" if (not unexpired or order.status != "pending") else "failed"
        if reconciliation:
            db.delete(reconciliation)
    except PortOneError:
        if reconciliation is None:
            reconciliation = PaymentReconciliation(
                purchase_id=order.purchase_id,
                payment_id=order.payment_id,
                status="refund_pending",
                created_at=now,
                updated_at=now,
            )
            db.add(reconciliation)
        else:
            reconciliation.updated_at = now
        # The recovery record is separate from the unique property reservation.
        # Keep the competing buyer's order untouched; only retain refund_pending on
        # this purchase when doing so does not violate the one-active-order index.
        if competing:
            if order.status == "pending":
                order.status = "cancelled"
        else:
            order.status = "refund_pending"
    order.updated_at = now
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=503, detail="Payment reconciliation could not be persisted"
        ) from exc
    return _confirm_response(order, db)
