import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from app.schemas.user import (
    KakaoCallbackReq,
    KakaoStateRes,
    CurrentUserRes,
    LoginReq,
    LoginRes,
    LogoutRes,
    SignUpReq,
    SignUpRes,
    SocialLoginRes,
)
from app.core.security import createToken
from app.models.user import User
from app.models.social_account import SocialAccount
from app.services.kakao_oauth import KakaoOAuthError, KakaoOAuthService, get_kakao_oauth_service
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.config import settings
from app.api.dependencies import get_current_user, is_configured_seller

router = APIRouter(prefix="/user", tags=["user"])


def unauthorized_session() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
    )


@router.get("/me", response_model=CurrentUserRes)
def current_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    social_account = db.scalar(
        select(SocialAccount).where(SocialAccount.user_idx == user.idx)
    )
    return {
        "name": user.name,
        "email": user.email,
        "provider": social_account.provider if social_account else "email",
        "role": "seller" if is_configured_seller(user.email) else "buyer",
    }


@router.post("/logout", response_model=LogoutRes)
def logout(response: Response):
    response.delete_cookie(
        "EN_AT",
        path="/",
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return {"ok": True}


def kakao_state_cookie_deletion_header() -> str:
    cookie_response = Response()
    cookie_response.delete_cookie(
        "KAKAO_OAUTH_STATE",
        path="/user/kakao",
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    return cookie_response.headers["set-cookie"]

# 제어의 역전 : IoC, 객체 생성이나 프로그램의 실행 흐름의 제어를 외부로 넘기는 프로그래밍 방식
# 의존성 주입 : DI, 필요한 객체를 우리가 직접 생성하지 않고 외부에서 전달해주는 방식
@router.post("/signup", response_model=SignUpRes)
def signup(req: SignUpReq, db: Session = Depends(get_db)):
    if is_configured_seller(req.email):
        seller_secret = settings.PROPERTY_SELLER_SECRET
        if not seller_secret.strip() or req.password != seller_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seller registration is not authorized",
            )

    # db = SessionLocal()

    user = db.scalar(select(User).where(User.email == req.email))
    if user:
        print("중복 가입")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 가입된 이메일입니다.")


    newUser = User(
        email=req.email, password=req.password, name=req.name
    )
    db.add(newUser)
    db.commit()
    return req

@router.post("/login", response_model=LoginRes)
def login(req: LoginReq, res: Response, db: Session = Depends(get_db)):
    # 회원 가입이 되어있는지 아닌지 확인
    user = db.scalar(select(User).where(User.email == req.email))
    seller_secret = settings.PROPERTY_SELLER_SECRET
    invalid_seller_secret = (
        user is not None
        and is_configured_seller(user.email)
        and (not seller_secret.strip() or req.password != seller_secret)
    )
    if not user or user.password != req.password or invalid_seller_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    res.set_cookie(
        "EN_AT",
        createToken(str(user.idx)),
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=1800,
    )
    return user


@router.post("/kakao/state", response_model=KakaoStateRes)
def create_kakao_state(response: Response):
    state = secrets.token_urlsafe(32)
    response.set_cookie(
        "KAKAO_OAUTH_STATE",
        state,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=300,
        path="/user/kakao",
    )
    return {"state": state}


@router.post("/kakao/callback", response_model=SocialLoginRes)
async def complete_kakao_login(
    req: KakaoCallbackReq,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    oauth: KakaoOAuthService = Depends(get_kakao_oauth_service),
):
    expected_state = request.cookies.get("KAKAO_OAUTH_STATE", "")
    if (
        not expected_state
        or not expected_state.isascii()
        or not req.state.isascii()
        or not secrets.compare_digest(expected_state, req.state)
    ):
        raise HTTPException(
            status_code=400,
            detail="카카오 로그인 요청을 확인할 수 없습니다. 다시 시도해 주세요.",
            headers={"Set-Cookie": kakao_state_cookie_deletion_header()},
        )

    try:
        profile = await oauth.fetch_profile(req.code)
    except KakaoOAuthError as exc:
        raise HTTPException(
            status_code=502,
            detail="카카오 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Set-Cookie": kakao_state_cookie_deletion_header()},
        ) from exc

    social_account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.provider == "kakao",
            SocialAccount.provider_user_id == profile["id"],
        )
    )
    if social_account:
        user = db.get(User, social_account.user_idx)
    else:
        user = User(name=profile["nickname"], email=None, password=None)
        db.add(user)
        db.flush()
        db.add(
            SocialAccount(
                user_idx=user.idx,
                provider="kakao",
                provider_user_id=profile["id"],
            )
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
            # A simultaneous first login can win the unique provider-id constraint.
            social_account = db.scalar(
                select(SocialAccount).where(
                    SocialAccount.provider == "kakao",
                    SocialAccount.provider_user_id == profile["id"],
                )
            )
            if not social_account:
                raise HTTPException(
                    status_code=500,
                    detail="카카오 계정을 저장하지 못했습니다.",
                    headers={"Set-Cookie": kakao_state_cookie_deletion_header()},
                )
            user = db.get(User, social_account.user_idx)

    response.delete_cookie("KAKAO_OAUTH_STATE", path="/user/kakao")
    response.set_cookie(
        "EN_AT",
        createToken(str(user.idx)),
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=1800,
    )
    return {"ok": True}

