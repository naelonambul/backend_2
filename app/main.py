# 전체 서버 진입점, FastAPI 객체 생성, 라우터 등록, 테이블 생성

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging_config import configure_logging
from app.core.http_logging import HttpAccessLogMiddleware

configure_logging()

from app.api.routers import user, board, property, purchase, questions
from app.db.database import Base, engine
from app.models.board import Board
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.property import Property
from app.models.purchase import Purchase
from app.models.payment_reconciliation import PaymentReconciliation
from app.models.question import Question, QuestionAnswer
from app.core.config import settings

fastapi_app = FastAPI(title="노트 API", version="0.1.0")

# CORS 설정: 프론트엔드 HTML/JS에서의 비동기 API 호출 허용
cors_origins = list(dict.fromkeys([settings.FRONTEND_ORIGIN, "https://www.nenene.n-e.kr"]))

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(user.router)
fastapi_app.include_router(board.router)
fastapi_app.include_router(property.router)
fastapi_app.include_router(purchase.router)
fastapi_app.include_router(questions.router)

Base.metadata.create_all(bind=engine)

@fastapi_app.get("/")
def main():
    return {"message": "메인 페이지입니다."}


app = HttpAccessLogMiddleware(fastapi_app)

