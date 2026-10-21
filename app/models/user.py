# DB의 표와 1:1로 매핑되는 파일

from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.db.database import Base

class User(Base):
    __tablename__ = "user"

    idx: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True)
    password: Mapped[Optional[str]] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column()

