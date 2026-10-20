from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, is_configured_seller
from app.db.database import get_db
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyRead

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db)):
    return db.scalars(select(Property).order_by(Property.idx.desc())).all()


@router.get("/{idx}", response_model=PropertyRead)
def read_property(idx: int, db: Session = Depends(get_db)):
    property_record = db.get(Property, idx)
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return property_record


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
    return property_record
