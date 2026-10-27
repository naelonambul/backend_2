from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.api.routers.questions import create_s3_client
from app.core.config import settings


@pytest.fixture
def client(tmp_path):
    database_path = (tmp_path / "questions.db").as_posix()
    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(autoflush=False, bind=test_engine)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_question_list_starts_empty(client):
    response = client.get("/questions")

    assert response.status_code == 200
    assert response.json() == []


def test_question_can_be_created_read_updated_and_deleted(client):
    created = client.post(
        "/questions",
        json={
            "title": "질문 제목",
            "contents": "질문 내용",
            "image_url": None,
        },
    )

    assert created.status_code == 201
    question = created.json()
    assert question["title"] == "질문 제목"
    assert question["contents"] == "질문 내용"
    assert question["image_url"] is None
    assert question["answer"] is None

    fetched = client.get(f"/questions/{question['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == question

    updated = client.put(
        f"/questions/{question['id']}",
        json={
            "title": "수정된 질문",
            "contents": "수정된 내용",
            "image_url": None,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "수정된 질문"

    deleted = client.delete(f"/questions/{question['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/questions/{question['id']}").status_code == 404


def test_question_accepts_only_a_public_image_from_the_configured_bucket(client):
    created = client.post(
        "/questions",
        json={
            "title": "이미지 질문",
            "contents": "이미지 확인",
            "image_url": (
                "https://ckh-bucket-543587017444-ap-northeast-2-an.s3."
                "ap-northeast-2.amazonaws.com/questions/image.png"
            ),
        },
    )
    assert created.status_code == 201
    assert created.json()["image_url"].endswith("questions/image.png")

    invalid = client.post(
        "/questions",
        json={
            "title": "외부 이미지",
            "contents": "외부 주소는 거절",
            "image_url": "https://example.com/image.png",
        },
    )
    assert invalid.status_code == 422


def test_question_has_at_most_one_answer_and_answer_can_be_updated_and_removed(client):
    question = client.post(
        "/questions",
        json={"title": "질문", "contents": "내용"},
    ).json()

    first_answer = client.post(
        f"/questions/{question['id']}/answer", json={"contents": "첫 답변"}
    )
    assert first_answer.status_code == 201
    assert first_answer.json()["answer"]["contents"] == "첫 답변"

    duplicate = client.post(
        f"/questions/{question['id']}/answer", json={"contents": "두 번째 답변"}
    )
    assert duplicate.status_code == 409

    updated = client.put(
        f"/questions/{question['id']}/answer", json={"contents": "수정 답변"}
    )
    assert updated.status_code == 200
    assert updated.json()["answer"]["contents"] == "수정 답변"

    deleted = client.delete(f"/questions/{question['id']}/answer")
    assert deleted.status_code == 204
    assert client.get(f"/questions/{question['id']}").json()["answer"] is None


def test_answer_cannot_be_created_for_missing_question(client):
    response = client.post("/questions/999/answer", json={"contents": "답변"})

    assert response.status_code == 404


def test_presigned_upload_uses_a_generated_key_and_rejects_non_images(client, monkeypatch):
    fake_s3 = Mock()
    fake_s3.generate_presigned_url.return_value = "https://signed.example/upload"
    monkeypatch.setattr("app.api.routers.questions.create_s3_client", lambda: fake_s3)

    response = client.post(
        "/questions/presigned-upload",
        json={"filename": "my photo.png", "content_type": "image/png"},
    )

    assert response.status_code == 200
    assert response.json()["upload_url"] == "https://signed.example/upload"
    assert response.json()["image_url"].startswith(
        "https://ckh-bucket-543587017444-ap-northeast-2-an.s3.ap-northeast-2.amazonaws.com/questions/"
    )
    assert response.json()["image_url"].endswith(".png")
    params = fake_s3.generate_presigned_url.call_args.kwargs["Params"]
    assert params["ContentType"] == "image/png"
    assert params["Key"].startswith("questions/")

    invalid = client.post(
        "/questions/presigned-upload",
        json={"filename": "file.exe", "content_type": "application/octet-stream"},
    )
    assert invalid.status_code == 422


def test_s3_presigned_url_uses_the_bucket_region_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "AWS_REGION", "ap-northeast-2")
    monkeypatch.setattr(settings, "AWS_S3_BUCKET_NAME", "example-bucket")
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "test-secret-key")

    upload_url = create_s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.AWS_S3_BUCKET_NAME,
            "Key": "questions/image.png",
            "ContentType": "image/png",
        },
        ExpiresIn=300,
    )

    assert urlsplit(upload_url).hostname == (
        "example-bucket.s3.ap-northeast-2.amazonaws.com"
    )
