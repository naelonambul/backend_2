# 하벤 홈 부동산 플랫폼

FastAPI와 Vue 3로 만든 온라인 부동산 매물 서비스입니다. 지정된 판매자 한 명이 매물을 등록하고, 구매자는 매물을 조회한 뒤 PortOne 결제창에서 구매할 수 있습니다.

## 주요 기능

- 매물 목록과 상세 정보 조회, 가격·면적·방 개수·주소 표시
- 지정된 판매자 계정만 매물 등록
- 이메일·비밀번호 및 카카오 로그인
- 구매자의 매물 전액 결제: PortOne V2, Toss Payments 신모듈
- 서버가 매물 가격과 PortOne 결제 상태·금액·통화를 확인한 뒤 구매 완료 처리
- `available`(구매 가능), `reserved`(결제 진행 중), `sold`(판매 완료) 상태 표시
- 15분 주문 예약, 중복 구매 방지, 취소 재시도 기록

결제 테스트용으로 100원, 1,000원, 10,000원 매물이 현재 로컬 `app.db`에 등록돼 있습니다. 현재 DB에서는 100원 매물이 결제 완료 상태이고 나머지 두 매물은 테스트용으로 사용할 수 있습니다. 이 데이터는 저장소를 새로 내려받았을 때 자동으로 생성되지는 않습니다.

## 기술 스택

- 프런트엔드: Vue 3, Vite, Vue Router, Jest
- 백엔드: FastAPI, SQLAlchemy, Pydantic Settings
- 데이터베이스: SQLite (`app.db`)
- 로그인: 이메일·비밀번호, 카카오 OAuth
- 결제: PortOne V2 Browser SDK 및 REST API, Toss Payments 신모듈

## 폴더 구성

```text
app/                  FastAPI 앱, API 라우터, 데이터 모델, 결제 서비스
frontend/             Vue 앱, 매물 화면, 카카오 로그인, PortOne 결제
tests/                백엔드 pytest 테스트
docs/superpowers/     결제 설계서와 구현 계획
app.db                로컬 SQLite 데이터베이스
```

## 환경 설정

PowerShell에서 저장소 루트의 예시 파일을 복사합니다.

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
```

### 백엔드 `.env`

| 변수 | 용도 |
| --- | --- |
| `PROPERTY_SELLER_EMAIL` | 판매자 권한을 받을 단일 이메일 주소 |
| `PROPERTY_SELLER_SECRET` | 지정 판매자 계정 등록·로그인에 사용할 비밀번호 |
| `PORTONE_API_SECRET` | 서버가 PortOne V2 결제를 조회·취소할 때 사용하는 비밀 키 |
| `KAKAO_REST_API_KEY` | 카카오 OAuth 토큰 교환용 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 카카오 앱에서 사용하는 경우의 클라이언트 시크릿 |
| `KAKAO_REDIRECT_URI` | 카카오 로그인 콜백 주소. 기본값은 `http://127.0.0.1:5173/auth/kakao/callback` |
| `FRONTEND_ORIGIN` | CORS 허용 프런트엔드 주소. 기본값은 `http://127.0.0.1:5173` |
| `BACKEND_ORIGIN` | 백엔드 주소. 기본값은 `http://127.0.0.1:8000` |
| `SESSION_COOKIE_SECURE` | HTTPS 환경에서는 `true`, 로컬 HTTP 개발에서는 `false` |
| `SESSION_COOKIE_SAMESITE` | 세션 쿠키 SameSite 설정. 기본값은 `lax` |

`PROPERTY_SELLER_EMAIL`에 지정한 계정만 판매자입니다. 이 계정은 `PROPERTY_SELLER_SECRET`과 일치하는 비밀번호로 등록·로그인해야 하며, 다른 가입자는 구매자 권한을 갖습니다. 카카오로 새로 로그인한 계정도 구매자로 생성됩니다.

### 프런트엔드 `frontend/.env.local`

| 변수 | 용도 |
| --- | --- |
| `VITE_PORTONE_STORE_ID` | PortOne 상점 식별자 |
| `VITE_PORTONE_CHANNEL_KEY` | Toss Payments 신모듈 채널 키 |
| `VITE_KAKAO_JAVASCRIPT_KEY` | 카카오 JavaScript 키 |
| `VITE_KAKAO_REDIRECT_URI` | 카카오 로그인 콜백 주소 |

프런트엔드 변수는 브라우저에 전달될 수 있으므로 공개 가능한 키만 입력합니다. `PORTONE_API_SECRET`, 판매자 비밀번호, 카카오 REST API 키와 클라이언트 시크릿은 프런트엔드 설정에 넣지 마세요. 환경변수를 바꾼 뒤에는 백엔드와 Vite 서버를 다시 시작해야 합니다.

### 카카오 로그인

카카오디벨로퍼스 앱의 웹 플랫폼에 `http://127.0.0.1:5173`을 등록하고, Redirect URI로 `http://127.0.0.1:5173/auth/kakao/callback`을 등록합니다. 이 주소를 백엔드 `.env`의 `KAKAO_REDIRECT_URI`와 프런트엔드 설정의 `VITE_KAKAO_REDIRECT_URI`에 동일하게 지정합니다.

### PortOne 결제

PortOne 채널은 Toss Payments PG와 신모듈로 설정합니다. 앱은 설정된 채널의 상점 ID와 채널 키를 프런트엔드에서 사용하고, PortOne V2 API 비밀 키로 백엔드에서 결제를 검증합니다. 기존 PortOne 채널이나 다른 대시보드 설정은 앱 실행을 위해 변경할 필요가 없습니다. PG MID와 PG 인증 정보는 PortOne 콘솔의 채널 설정에 보관하고 저장소에는 기록하지 마세요.

주문 금액은 브라우저 입력값이 아니라 DB의 매물 가격으로 정합니다. 결제 후 백엔드가 PortOne에서 결제 정보를 다시 조회해 주문 ID, 결제 상태, 정확한 금액, 통화를 확인합니다. 결제창의 성공 화면만으로는 매물이 판매 완료 처리되지 않습니다.

## 실행

Python 의존성을 설치하고 저장소 루트에서 백엔드 서버를 실행합니다.

```powershell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

별도의 PowerShell 창에서 프런트엔드를 실행합니다.

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

브라우저에서 `http://127.0.0.1:5173`에 접속합니다. API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다. 기본 DB 경로는 저장소 루트의 `app.db`이며, 서버 시작 시 모델 테이블이 생성됩니다.

## 화면과 API

| 기능 | 화면/API | 권한 |
| --- | --- | --- |
| 매물 목록 | `/properties`, `GET /properties` | 공개 |
| 매물 상세 | `/properties/:idx`, `GET /properties/{idx}` | 공개 |
| 매물 등록 | `/properties/new`, `POST /properties` | 지정 판매자 |
| 이메일 회원가입·로그인 | `/signup`, `/login`, `POST /user/signup`, `POST /user/login` | 공개 |
| 카카오 로그인 | `/auth/kakao/callback`, `/user/kakao/*` | 공개 |
| 현재 로그인 사용자 | `GET /user/me` | 로그인 필요 |
| 결제 주문 생성 | `POST /properties/{property_idx}/purchases` | 구매자 |
| 결제 확인 | `POST /purchases/{purchase_id}/confirm` | 해당 주문의 구매자 |

매물 조회 API는 `availability`를 포함합니다. 진행 중 주문은 15분 동안 매물을 예약하고, 구매가 확인되면 판매 완료로 바뀝니다. 동일 매물의 중복 주문은 DB 제약과 서버 검증으로 막습니다.

## 테스트와 빌드

저장소 루트에서 백엔드 테스트를 실행합니다.

```powershell
python -m pytest -q
```

프런트엔드 테스트와 빌드는 `frontend` 폴더에서 실행합니다.

```powershell
cd frontend
npm test
npm run build
```

자동화 테스트는 PortOne API를 모의 처리하므로 실제 PG 승인 없이 실행할 수 있습니다. 실제 결제 테스트는 PortOne 테스트 채널과 테스트용 매물로 진행하세요.
