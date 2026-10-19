
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class Board(Base):
    __tablename__ = "board"

    idx: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    contents: Mapped[str] = mapped_column()

