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

브라우저에서 Vite가 안내하는 주소(기본값 `http://127.0.0.1:5173`)를 열고, 프론트엔드의 API 서버 주소가 `http://127.0.0.1:8000`인지 확인하세요.

화면 경로는 `/signup`, `/login`, `/boards`, `/boards/new`, `/boards/:idx`이며, `/`는 게시글 목록으로 이동합니다.

## 검증

```bash
python -m pytest
cd frontend
npm test
npm run build
```

## 카카오 로그인 설정

1. 카카오디벨로퍼스 앱에서 웹 플랫폼 도메인 `http://127.0.0.1:5173`과 Redirect URI `http://127.0.0.1:5173/auth/kakao/callback`을 등록합니다.
2. 저장소 루트의 `.env.example`을 `.env`로 복사하고 `KAKAO_REST_API_KEY`와 필요한 경우 `KAKAO_CLIENT_SECRET`을 입력합니다.
3. `frontend/.env.example`을 `frontend/.env.local`로 복사하고 `VITE_KAKAO_JAVASCRIPT_KEY`를 입력합니다. 백엔드와 프런트엔드의 Redirect URI 값은 같아야 합니다.
4. FastAPI와 Vite 개발 서버를 다시 시작한 뒤 `/login`에서 카카오 로그인을 확인합니다.

프런트엔드에는 공개 JavaScript 키만 둡니다. REST API 키와 클라이언트 시크릿은 백엔드 `.env`에만 저장합니다. 카카오 로그인이 처음 성공하면 닉네임으로 사용자를 만들고, 이후에는 카카오 회원 번호에 연결된 계정을 재사용합니다. 이메일 정보는 요청하지 않습니다.
