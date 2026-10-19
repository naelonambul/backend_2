# 모아 노트 API workspace

FastAPI 백엔드와 Vue 3 프론트엔드로 구성된 노트 API 작업 공간입니다.

## 실행

백엔드 의존성을 설치하고 API 서버를 실행합니다.

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

별도의 터미널에서 Vue 개발 서버를 실행합니다.

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 Vite가 안내하는 주소(기본값 `http://localhost:5173`)를 열고, 화면 상단의 API 서버 주소가 `http://localhost:8000`인지 확인하세요.

화면 경로는 `/signup`, `/login`, `/boards`, `/boards/new`, `/boards/:idx`이며, `/`는 게시글 목록으로 이동합니다.

## 검증

```bash
python -m pytest
cd frontend
npm test
npm run build
```
