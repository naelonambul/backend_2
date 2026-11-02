from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Property(Base):
    __tablename__ = "property"

    idx: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300))
    price_krw: Mapped[int] = mapped_column()
    area_m2: Mapped[float] = mapped_column()
    room_count: Mapped[int] = mapped_column()
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller_user_idx: Mapped[int] = mapped_column(ForeignKey("user.idx"), nullable=False)
