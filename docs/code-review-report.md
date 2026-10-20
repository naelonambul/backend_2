# 코드 리뷰 보고서

- 검토일: 2026-10-20
- 검토 범위: Vue 프론트엔드와 FastAPI 백엔드
- 검토 방식: 프론트엔드·백엔드 독립 서브에이전트 리뷰 후 근거 대조
- 요약: 높음 2건, 중간 5건, 낮음 2건
- 이번 작업은 읽기 전용 검토입니다. 소스 코드는 수정하지 않았습니다.

## 프론트엔드

### 중간 — 모바일 화면에서 로그인·회원가입으로 이동하기 어려움

화면 너비가 640px 이하일 때 헤더 로그인 링크가 숨겨집니다. 게시글 목록에는 로그인이나 회원가입으로 가는 다른 링크가 없어 모바일 사용자는 해당 화면에 직접 주소를 입력해야 합니다.

- 근거: [`App.vue`](../frontend/src/App.vue#L23), [`style.css`](../frontend/src/style.css#L1340)
- 권장 수정: 모바일에서도 계정 또는 로그인 진입 링크를 노출합니다.

### 중간 — 게시글 상세 URL의 번호가 바뀌어도 이전 글이 표시될 수 있음

상세 화면은 `onMounted`에서만 데이터를 불러오고 `route.params.idx`를 사용합니다. Vue Router가 상세 컴포넌트를 재사용하면 URL의 `idx`가 바뀌어도 새 데이터를 불러오지 않을 수 있습니다.

- 재현 예: `/boards/1`과 `/boards/2`를 방문한 뒤 브라우저 뒤로·앞으로 가기를 사용합니다.
- 근거: [`BoardDetailPage.vue`](../frontend/src/pages/BoardDetailPage.vue#L12), 특히 `onMounted(loadNote)` 호출
- 권장 수정: `route.params.idx` 변경을 감시해 다시 불러오고, 매개변수 변경 사례를 Jest 테스트로 추가합니다.

### 낮음 — 브라우저 뒤로 가기 후 스크롤 위치가 복원되지 않음

라우터의 `scrollBehavior`가 항상 맨 위를 반환해, 목록으로 돌아올 때 기존 스크롤 위치를 잃습니다.

- 근거: [`router.js`](../frontend/src/router.js#L15)
- 권장 수정: 저장된 위치가 있으면 `savedPosition`을 반환합니다.

### 낮음 — 키보드 사용자가 헤더를 건너뛸 수 있는 링크가 없음

모든 경로에서 헤더 링크들을 탭으로 통과해야 본문에 도달합니다. 본문 `<main>`에 대상으로 삼을 ID도 없습니다.

- 근거: [`App.vue`](../frontend/src/App.vue#L9), 본문 시작 부분 [`App.vue`](../frontend/src/App.vue#L37)
- 권장 수정: `<main>`에 ID를 주고 헤더를 건너뛰는 skip link를 추가합니다.

## 백엔드

### 높음 — 비밀번호가 평문으로 저장되고 비교됨

회원가입 시 요청의 비밀번호를 그대로 `User`에 저장하고 로그인 시 입력값과 직접 비교합니다. DB 파일이나 백업이 노출되면 모든 사용자의 비밀번호를 바로 확인할 수 있습니다.

- 근거: [`user.py`](../app/api/routers/user.py#L100), 저장된 비밀번호와 직접 비교하는 [`user.py`](../app/api/routers/user.py#L111)
- 권장 수정: 회원가입에서 Argon2id 또는 bcrypt로 해시하고, 로그인에서는 안전한 검증 함수를 사용합니다.

### 높음 — JWT 서명 키에 알려진 기본값이 있음

`SECRET_KEY`가 소스에 포함된 기본 문자열을 사용합니다. 운영 환경에 별도 키가 설정되지 않으면 이 값을 아는 사람이 세션 토큰을 위조할 수 있습니다. 현재 `.env.example`에도 `SECRET_KEY` 설정 항목이 없습니다.

- 근거: [`config.py`](../app/core/config.py#L8), [`.env.example`](../.env.example)
- 권장 수정: 운영 환경에서 생성된 비밀 키를 필수로 받고, 기본 키가 남아 있으면 애플리케이션 시작을 실패시킵니다.

### 중간 — 테스트가 실제 설정 DB에 테이블을 만들 수 있음

`tests/test_api.py`가 `app.main`을 가져오면, 테스트의 임시 DB fixture가 적용되기 전에 `app.main`의 모듈 코드가 설정된 기본 엔진에 `create_all`을 실행합니다. pytest가 개발 DB 파일에 영향을 줄 수 있습니다.

- 근거: [`test_api.py`](../tests/test_api.py#L7), [`main.py`](../app/main.py#L30), 엔진 생성 위치 [`database.py`](../app/db/database.py#L12)
- 권장 수정: 모듈 import 시 테이블을 만들지 않도록 하고, 테스트는 임시 DB에서만 스키마를 초기화합니다.

### 중간 — 기본 SQLite 파일명이 프로젝트 설정과 다름

프로젝트 설정은 `app.db`를 사용한다고 되어 있지만, 기본 `DATABASE_URL`은 `db.sqlite`입니다. `.env.example`에 `DATABASE_URL`이 없으므로 새 환경은 `db.sqlite`를 생성합니다.

- 근거: [`config.py`](../app/core/config.py#L10), [`.env.example`](../.env.example)
- 권장 수정: 기본 경로를 `app.db`로 바꾸거나 `.env.example`에 사용할 DB 경로를 명시합니다.

### 중간 — 게시판 쓰기가 공개되어 있고 요청·목록 크기 제한이 없음

게시글 등록은 인증이나 속도 제한 없이 호출할 수 있고, 입력 스키마는 제목과 본문 길이를 제한하지 않습니다. 목록 API는 전체 게시글과 본문을 한 번에 반환합니다. 반복 또는 대용량 요청으로 저장 공간과 응답 자원을 소모시킬 수 있습니다.

- 근거: 공개 등록 [`board.py`](../app/api/routers/board.py#L12), 전체 목록 반환 [`board.py`](../app/api/routers/board.py#L23), 길이 제한이 없는 [`board.py` 스키마](../app/schemas/board.py#L12)
- 권장 수정: 요청 크기와 필드 길이를 제한하고 목록에 페이지네이션을 추가합니다. 익명 게시가 제품 요구가 아니라면 인증도 요구합니다.

## 권장 처리 순서

1. 비밀번호 해싱과 JWT 키 필수화
2. 테스트 DB 초기화 분리와 기본 DB 파일명 정합성
3. 게시판 입력·목록 제한
4. 모바일 계정 진입과 상세 경로 변경 버그
5. 스크롤 복원과 키보드 skip link
