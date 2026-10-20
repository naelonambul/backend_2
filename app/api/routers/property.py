from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, is_configured_seller
from app.db.database import get_db
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyRead
from app.models.payment_reconciliation import PaymentReconciliation
from app.models.purchase import Purchase, utc_now

router = APIRouter(prefix="/properties", tags=["properties"])


def _property_response(property_record: Property, db: Session):
    now = utc_now()
    active = db.scalars(
        select(Purchase.status).where(
            Purchase.property_idx == property_record.idx,
            (
                Purchase.status.in_(("paid", "refund_pending"))
                | ((Purchase.status == "pending") & (Purchase.expires_at > now))
            ),
        )
    ).all()
    # Reconciliation is keyed by purchase, so query by the property through its purchase.
    has_reconciliation = db.scalar(
        select(PaymentReconciliation.purchase_id)
        .join(Purchase, Purchase.purchase_id == PaymentReconciliation.purchase_id)
        .where(Purchase.property_idx == property_record.idx)
    ) is not None
    if "paid" in active:
        availability = "sold"
    elif active or has_reconciliation:
        availability = "reserved"
    else:
        availability = "available"
    return {
        **PropertyRead.model_validate(property_record, from_attributes=True).model_dump(),
        "availability": availability,
    }


@router.get("", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db)):
    properties = db.scalars(select(Property).order_by(Property.idx.desc())).all()
    return [_property_response(item, db) for item in properties]


@router.get("/{idx}", response_model=PropertyRead)
def read_property(idx: int, db: Session = Depends(get_db)):
    property_record = db.get(Property, idx)
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return _property_response(property_record, db)


@router.post("", response_model=PropertyRead)
def create_property(
    request: PropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not is_configured_seller(user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller access required")

    property_record = Property(
        **request.model_dump(exclude={"image_url"}),
        image_url=str(request.image_url) if request.image_url is not None else None,
        seller_user_idx=user.idx,
    )
    db.add(property_record)
    db.commit()
    db.refresh(property_record)
    return _property_response(property_record, db)
