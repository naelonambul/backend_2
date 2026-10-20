from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PurchaseCreateResponse(BaseModel):
    purchase_id: str
    payment_id: str
    order_name: str
    amount: int
    currency: Literal["KRW"]
    expires_at: datetime


class PurchaseConfirmRequest(BaseModel):
    payment_id: str = Field(min_length=1, max_length=100)


class PurchaseConfirmResponse(BaseModel):
    purchase_id: str
    status: Literal["pending", "paid", "failed", "cancelled", "refund_pending"]
