# ORM : Object Relation Mapping
# 객체 : 현실 세상의 무언가를 컴퓨터 코드로 옮긴 것
# 개체 : 현실 세상의 무언가를 컴퓨터의 데이터로 옮긴 것


# DB 서버와 연결 설정하는 파일

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings
# DB 연결을 관리하는 엔진
engine = create_engine(settings.database_url, echo=False)
read_engine = (
    create_engine(settings.read_database_url, echo=False)
    if settings.read_database_url != settings.database_url
    else engine
)
# DB 작업용 세션을 만드는 도구
SessionLocal = sessionmaker(autoflush=False, bind=engine)
ReadSessionLocal = sessionmaker(autoflush=False, bind=read_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db():
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()

# 모델들이 상속받을 부모 클래스
class Base(DeclarativeBase):
    # 모든 테이블이 가지는 속성을 지정
    pass
