from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.purchase import utc_now


class PaymentReconciliation(Base):
    """Durable retry record for a captured payment whose cancellation is unresolved."""

    __tablename__ = "payment_reconciliation"

    purchase_id: Mapped[str] = mapped_column(
        ForeignKey("purchase.purchase_id"), primary_key=True
    )
    payment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="refund_pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
