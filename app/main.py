# 전체 서버 진입점, FastAPI 객체 생성, 라우터 등록, 테이블 생성

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routers import user, board, property
from app.db.database import Base, engine
from app.models.board import Board
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.property import Property
from app.core.config import settings

app = FastAPI(title="노트 API", version="0.1.0")

# CORS 설정: 프론트엔드 HTML/JS에서의 비동기 API 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(board.router)
app.include_router(property.router)

Base.metadata.create_all(bind=engine)

# frontend 폴더가 존재할 경우 정적 파일 서빙 마운트
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def main():
    return {"message": "메인 페이지입니다."}

