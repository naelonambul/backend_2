# 클라이언트로부터 받는 데이터의 형식   HTTP 요청에 포함된 데이터
# 클라이언트에게 전달해줄 데이터의 형식  HTTP 응답에 포함된 데이터

from pydantic import BaseModel

class SignUpReq(BaseModel):
    email: str
    password: str
    name: str

class SignUpRes(BaseModel):
    email: str
    name: str


class LoginReq(BaseModel):
    email: str
    password: str

class LoginRes(BaseModel):
    email: str