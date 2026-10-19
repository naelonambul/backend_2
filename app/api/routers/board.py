from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models.board import Board
from app.schemas.board import RegisterReq, RegisterRes, ReadRes

router = APIRouter(prefix="/board", tags=["board"])


@router.post("/register", response_model=RegisterRes)
def register(req: RegisterReq, db: Session = Depends(get_db)):
    board = Board(
        title=req.title, contents=req.contents
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@router.get("/list", response_model=list[ReadRes])
def list_boards(db: Session = Depends(get_db)):
    boards = db.scalars(select(Board).order_by(Board.idx.desc())).all()
    return [
        {"idx": board.idx, "title": board.title, "contents": board.contents}
        for board in boards
    ]


@router.get("/read/{idx}", response_model=ReadRes)
def read(idx: int, db: Session = Depends(get_db)):
    board = db.get(Board, idx)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노트를 찾을 수 없습니다.")
    return board













