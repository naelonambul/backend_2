# 보안상 중요한 값이나 기능들을 모아둔 파일, 토큰 생성, 비밀번호 암호화 등

from datetime import datetime, timedelta, timezone
import jwt
from app.core.config import settings


def createToken(userId: str):
    from datetime import timezone
    payload = {
        "sub": userId,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# 토큰 확인하는 함수
# 토큰에서 원하는 값을 가져오는 함수
# 비밀번호를 암호화 하는 함수
# 비밀번호 확인
