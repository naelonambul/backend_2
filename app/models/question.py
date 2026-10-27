from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    contents: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    answer: Mapped["QuestionAnswer | None"] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
    )


class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), unique=True, index=True
    )
    contents: Mapped[str] = mapped_column(Text)
    question: Mapped[Question] = relationship(back_populates="answer")
