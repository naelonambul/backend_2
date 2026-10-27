from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.database import get_db
from app.models.question import Question, QuestionAnswer
from app.schemas.question import (
    AnswerRead,
    AnswerWrite,
    PresignedUploadRequest,
    PresignedUploadResponse,
    QuestionRead,
    QuestionWrite,
)

router = APIRouter(prefix="/questions", tags=["questions"])

IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def create_s3_client():
    import boto3
    from botocore.config import Config

    kwargs = {
        "region_name": settings.AWS_REGION,
        "config": Config(s3={"addressing_style": "virtual"}),
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def _public_image_url(key: str) -> str:
    host = f"{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com"
    return f"https://{host}/{key}"


def _validate_image_url(image_url: str | None) -> None:
    if image_url is None:
        return

    parsed = urlsplit(image_url)
    allowed_hosts = {
        f"{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com",
        f"{settings.AWS_S3_BUCKET_NAME}.s3.amazonaws.com",
    }
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or not parsed.path.strip("/")
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="image_url must point to an image in the configured S3 bucket",
        )


def _question_read(question: Question) -> QuestionRead:
    return QuestionRead(
        id=question.id,
        title=question.title,
        contents=question.contents,
        image_url=question.image_url,
        answer=(
            AnswerRead(id=question.answer.id, contents=question.answer.contents)
            if question.answer is not None
            else None
        ),
    )


def _get_question(db: Session, question_id: int) -> Question:
    question = db.scalar(
        select(Question)
        .options(selectinload(Question.answer))
        .where(Question.id == question_id)
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return question


@router.get("", response_model=list[QuestionRead])
def list_questions(db: Session = Depends(get_db)):
    questions = db.scalars(
        select(Question)
        .options(selectinload(Question.answer))
        .order_by(Question.id.desc())
    ).all()
    return [_question_read(question) for question in questions]


@router.post("", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
def create_question(request: QuestionWrite, db: Session = Depends(get_db)):
    _validate_image_url(request.image_url)
    question = Question(**request.model_dump())
    db.add(question)
    db.commit()
    return _question_read(_get_question(db, question.id))


@router.get("/{question_id}", response_model=QuestionRead)
def read_question(question_id: int, db: Session = Depends(get_db)):
    return _question_read(_get_question(db, question_id))


@router.put("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    request: QuestionWrite,
    db: Session = Depends(get_db),
):
    _validate_image_url(request.image_url)
    question = _get_question(db, question_id)
    question.title = request.title
    question.contents = request.contents
    question.image_url = request.image_url
    db.commit()
    return _question_read(_get_question(db, question_id))


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    question = _get_question(db, question_id)
    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{question_id}/answer",
    response_model=QuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_answer(
    question_id: int,
    request: AnswerWrite,
    db: Session = Depends(get_db),
):
    question = _get_question(db, question_id)
    if question.answer is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Answer already exists")

    db.add(QuestionAnswer(question_id=question_id, contents=request.contents))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Answer already exists"
        )
    return _question_read(_get_question(db, question_id))


@router.put("/{question_id}/answer", response_model=QuestionRead)
def update_answer(
    question_id: int,
    request: AnswerWrite,
    db: Session = Depends(get_db),
):
    question = _get_question(db, question_id)
    if question.answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
    question.answer.contents = request.contents
    db.commit()
    return _question_read(_get_question(db, question_id))


@router.delete("/{question_id}/answer", status_code=status.HTTP_204_NO_CONTENT)
def delete_answer(question_id: int, db: Session = Depends(get_db)):
    question = _get_question(db, question_id)
    if question.answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
    db.delete(question.answer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/presigned-upload", response_model=PresignedUploadResponse)
def create_presigned_upload(request: PresignedUploadRequest):
    extension = IMAGE_EXTENSIONS.get(request.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only JPEG, PNG, GIF, and WebP images are supported",
        )
    if not settings.AWS_S3_BUCKET_NAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image uploads are not configured",
        )

    key = f"questions/{uuid4()}.{extension}"
    try:
        upload_url = create_s3_client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_S3_BUCKET_NAME,
                "Key": key,
                "ContentType": request.content_type,
            },
            ExpiresIn=300,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create an image upload URL",
        ) from exc

    return PresignedUploadResponse(
        upload_url=upload_url,
        image_url=_public_image_url(key),
    )
