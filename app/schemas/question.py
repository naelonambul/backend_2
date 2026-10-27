from pydantic import BaseModel, Field


class QuestionWrite(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    contents: str = Field(min_length=1)
    image_url: str | None = None


class AnswerWrite(BaseModel):
    contents: str = Field(min_length=1)


class AnswerRead(BaseModel):
    id: int
    contents: str


class QuestionRead(BaseModel):
    id: int
    title: str
    contents: str
    image_url: str | None
    answer: AnswerRead | None


class PresignedUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str


class PresignedUploadResponse(BaseModel):
    upload_url: str
    image_url: str
