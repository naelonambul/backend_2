from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Purchase(Base):
    __tablename__ = "purchase"
    __table_args__ = (
        Index(
            "uq_purchase_active_property",
            "property_idx",
            unique=True,
            sqlite_where=text("status IN ('pending', 'paid', 'refund_pending')"),
        ),
    )

    purchase_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    property_idx: Mapped[int] = mapped_column(ForeignKey("property.idx"), nullable=False)
    buyer_user_idx: Mapped[int] = mapped_column(ForeignKey("user.idx"), nullable=False)
    amount_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utc_now() + timedelta(minutes=15), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
