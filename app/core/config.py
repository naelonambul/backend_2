# 환경 설정 파일 : DB 접속 주소, 토큰 시크릿 등 환경변수로 설정된 값을 불러오는 파일

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    SECRET_KEY: str = "my-secret-key-for-jwt-must-be-32-bytes-or-more"
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite:///app.db"
    PROPERTY_SELLER_EMAIL: str = ""
    PROPERTY_SELLER_SECRET: str = ""
    PORTONE_API_SECRET: str = ""
    FRONTEND_ORIGIN: str = "http://127.0.0.1:5173"
    BACKEND_ORIGIN: str = "http://127.0.0.1:8000"
    DOMAIN: str = "nenene.n-e.kr"
    KAKAO_REST_API_KEY: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://127.0.0.1:5173/auth/kakao/callback"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_BUCKET_NAME: str = "ckh-bucket-543587017444-ap-northeast-2-an"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

settings = Settings()
