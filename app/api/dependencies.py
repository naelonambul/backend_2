import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User


def unauthorized_session() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("EN_AT")
    if not token:
        raise unauthorized_session()

    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_idx = int(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized_session()

    user = db.get(User, user_idx)
    if user is None:
        raise unauthorized_session()
    return user


def is_configured_seller(email: str | None) -> bool:
    seller_email = settings.PROPERTY_SELLER_EMAIL.strip().casefold()
    account_email = (email or "").strip().casefold()
    return bool(seller_email and account_email and account_email == seller_email)
