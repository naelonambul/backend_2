from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SocialAccount(Base):
    __tablename__ = "social_account"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
    )

    idx: Mapped[int] = mapped_column(primary_key=True)
    user_idx: Mapped[int] = mapped_column(ForeignKey("user.idx", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
