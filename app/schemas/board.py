from pydantic import BaseModel

#조회용 요청 X

#조회용 응답, 번호, 제목, 내용
class ReadRes(BaseModel):
    idx: int
    title: str
    contents: str

#작성용 요청, 제목, 내용
class RegisterReq(BaseModel):
    title: str
    contents: str
#작성용 응답, 번호, 제목, 내용
class RegisterRes(BaseModel):
    idx: int
    title: str
    contents: str