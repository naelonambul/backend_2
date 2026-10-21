from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Property(Base):
    __tablename__ = "property"

    idx: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    address: Mapped[str] = mapped_column()
    price_krw: Mapped[int] = mapped_column()
    area_m2: Mapped[float] = mapped_column()
    room_count: Mapped[int] = mapped_column()
    description: Mapped[str] = mapped_column()
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    seller_user_idx: Mapped[int] = mapped_column(ForeignKey("user.idx"), nullable=False)
