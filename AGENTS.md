# 기술 스택
frontend 폴더에 vue 프로젝트로 프론트엔드 개발
app 폴더에 fastapi 프로젝트로 백엔드 개발
DB는 SQllite 로 app.db 파일로 관리 

# 검증 
백엔드 pytest로 테스트할 수 잇는 테스트 코드 작성후 전체 통과되면 완료
프론트엔드는 jest로 테스트할 수 있는 테스트 코드 작성후 전체 통과되면 완료[App.vue](frontend/src/App.vue)[main.js](frontend/src/main.js)

## Codex 서브에이전트
- 다음 세션에서도 재사용하도록 프로젝트 서브에이전트 설정을 `.codex/agents/`에 유지한다.
- `backend_dev`와 `frontend_dev`는 코드 리뷰 전용 에이전트와 별개의 구현 에이전트다.
- `app/` 백엔드 작업은 `backend_dev`를 사용하고, `frontend/` 프론트엔드 작업은 `frontend_dev`를 사용한다.
- 양쪽이 독립적으로 진행될 수 있는 작업은 두 에이전트에 각각 범위를 나눠 맡긴다. API 계약이나 인증 흐름처럼 양쪽이 함께 결정해야 하는 변경은 메인 에이전트가 먼저 계약을 정리하고, 서로의 담당 폴더를 수정하지 않도록 한다.
- 메인 에이전트가 결과를 검토하고 통합한 뒤 프로젝트 검증 기준에 따라 확인한다.
