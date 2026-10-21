# Windows SSH Deployment Design

## Goal

Deploy the backend and frontend independently to the Windows server when changes reach `main`, using GitHub Actions for validation/build and password-authenticated SSH/SCP for delivery.

## Confirmed approach

GitHub Actions builds the deployment artifacts and copies them to the server. The server does not need a GitHub repository credential or a Node.js installation. The user selected this artifact-transfer approach.

The current workspace branch is `codex/house-marketplace`, which is 30 commits ahead of `main`. The deployment branch will be based on this workspace branch so it includes the current app. A PR from the new branch directly to `main` will include those existing commits as well as the deployment work.

## Workflow behavior

- Replace the existing placeholder `test.yml` with pull request validation for backend pytest and frontend Jest/build.
- Add a backend deployment workflow that validates changes to backend paths and deploys only on a push to `main`.
- Add a frontend deployment workflow that runs frontend Jest/build and deploys only on a push to `main`.
- Use folder path filters so unrelated changes do not deploy the other service. A merge to `main` produces the push event used by the deployment workflow.
- Do not give deployment secrets to pull request validation jobs.

## Backend deployment

- Package only `app/` and root `requirements.txt`; do not package `.env`, SQLite files, local virtual environments, or tests.
- Transfer the archive to `C:\server01` over SCP and run a PowerShell deployment script over SSH.
- Replace the server's `app/` tree and `requirements.txt`, preserving `C:\server01\.env` and `C:\server01\app.db`.
- Create or update `C:\server01\.venv`, install the requirements, and register a Windows Task Scheduler task that runs `C:\server01\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 9015` with `C:\server01` as its working directory.
- Restart the task after deployment and require a successful HTTP response from `http://127.0.0.1:9015/` before reporting success.
- Keep a copy of the prior `app/` tree and `requirements.txt` until the health check passes; restore them and restart the prior version if the new version fails its health check.

## Frontend and Nginx deployment

- Run `npm ci`, Jest, and `npm run build` in GitHub Actions. Build with `BACKEND_ORIGIN` set to the configured production API origin.
- Package and transfer `frontend/dist/` to `C:\Users\test\Downloads\nginx-1.30.5\html`, replacing old hashed assets.
- Keep a version-controlled Nginx configuration that listens on port `9115`, serves that `html` directory, and falls back to `/index.html` for Vue history routes.
- Back up the existing Nginx configuration once before installing the managed configuration.
- Register or update a Task Scheduler task to run Nginx from `C:\Users\test\Downloads\nginx-1.30.5` at startup. Restart it after deployment and require a successful HTTP response from `http://127.0.0.1:9115/`.
- Keep the prior static files and configuration until the health check passes; restore them and restart Nginx if the new deployment fails.

## SSH and application configuration

Configure these repository secrets under **Settings → Secrets and variables → Actions**:

- `DEPLOY_HOST` — defaults to the supplied server, `222.112.208.68`.
- `DEPLOY_PORT` — SSH port; this is separate from application ports `9015` and `9115`.
- `DEPLOY_USER` — Windows OpenSSH account with permission to write both deployment directories and manage scheduled tasks.
- `DEPLOY_PASSWORD` — password for that account.
- `DEPLOY_KNOWN_HOSTS` — pinned SSH host key entries for the server.

Use repository variables for non-sensitive build values such as `BACKEND_ORIGIN` (`http://222.112.208.68:9015`), `FRONTEND_ORIGIN` (`http://222.112.208.68:9115`), and the browser-visible Vite settings needed for Kakao and PortOne.

The workflow never replaces the backend `.env` or database. Before the first deployment, create `C:\server01\.env` with production backend secrets and set `FRONTEND_ORIGIN` to the deployed frontend origin. The workflow and server configuration use the assumption that `9015` is the FastAPI port and `9115` is the Nginx port; SSH uses the separately configured `DEPLOY_PORT`.

## Server prerequisites

- Windows OpenSSH Server accepts password authentication from GitHub-hosted Actions runners.
- The configured SSH account has administrator rights, Python 3, and write access to both supplied paths.
- The Nginx folder contains `nginx.exe`, `conf/`, and `mime.types`.
- Firewall rules allow inbound TCP traffic on the configured SSH port, `9015`, and `9115`.

## Failure handling and limits

- Fail deployment if artifact transfer, dependency installation, scheduled task startup, Nginx configuration validation, or either local HTTP health check fails.
- Preserve `.env` and `app.db` on every backend update. The application currently creates tables at startup and has no migration framework; this deployment design does not perform database migrations.
- Keep application ports and server paths fixed to the values supplied by the user. Keep SSH connection details in repository secrets.

## Files in the implementation

- `.github/workflows/test.yml` — pull request validation.
- `.github/workflows/deploy-backend.yml` — backend validation and main-branch deployment.
- `.github/workflows/deploy-frontend.yml` — frontend validation and main-branch deployment.
- `.github/deploy/backend.ps1` — backend extraction, environment preservation, task registration, restart, and health check.
- `.github/deploy/frontend.ps1` — frontend extraction, Nginx configuration install/restart, and health check.
- `.github/DEPLOYMENT.md` — secret and server setup instructions.
- `frontend/nginx.conf` — managed Windows Nginx configuration for port 9115 and Vue history fallback.
