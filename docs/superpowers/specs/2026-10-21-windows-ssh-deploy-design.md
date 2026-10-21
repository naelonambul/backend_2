# Windows SSH Deployment Design

## Goal

When backend or frontend changes reach `main`, package/build the changed service and transfer it to the Windows server over SSH/SCP. Run FastAPI on port `8000`; publish the frontend through the existing Nginx listeners on ports `80` and `443`. The backend deployment uses SSH port `9015`, and the frontend deployment uses SSH port `9115`. Deployment workflows do not run test suites.

## Delivery approach

GitHub Actions produces the deployable files and sends them to Windows. The server does not need a GitHub repository credential. Backend deployment packages `app/` and `requirements.txt`; frontend deployment runs the Vite production build and sends `frontend/dist/`.

The new branch is based on the current workspace branch, which is 30 commits ahead of `main`. A PR from that branch to `main` will include those existing commits as well as the deployment files.

## Workflow behavior

- Add separate backend and frontend workflows triggered by pushes to `main`, with path filters for each service.
- Backend workflow packages the backend source and requirements, uploads them via SSH port `9015`, installs/updates server dependencies, and restarts the FastAPI process.
- Frontend workflow runs `npm ci` and `npm run build`, uploads `dist/` via SSH port `9115`, and updates the existing Nginx document root. Nginx already serves ports `80` and `443`; do not replace its configuration or restart it for static-file changes.
- Do not add or run pytest or Jest in these deployment workflows. Leave the existing placeholder `.github/workflows/test.yml` unchanged.

## Backend deployment

- Package only `app/` and root `requirements.txt`; exclude `.env`, SQLite files, virtual environments, and tests.
- Transfer the archive to `C:\server01` and invoke a PowerShell deployment script over SSH.
- Replace the server's `app/` tree and `requirements.txt`, preserving `C:\server01\.env` and `C:\server01\app.db`.
- Require Python 3.10 or later. Install requirements into a new versioned virtual environment while the current task keeps running.
- Before switching, require port `8000` to be free after stopping the managed task. Refuse to deploy over a listener that is not owned by the expected running `MoaBackendApi` Python/Uvicorn process.
- Replace the app and requirements, register or update the startup scheduled task to use that environment, and run `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` with working directory `C:\server01`.
- Wait for the task to return HTTP 200 from `http://127.0.0.1:8000/` before committing the deployment. If startup fails, restore the previous app, requirements, and task environment; on a failed first deployment, unregister the new task before removing its environment.

## Frontend and Nginx deployment

- Run the Vite production build in GitHub Actions with `BACKEND_ORIGIN` set to the production API origin.
- Transfer the contents of `frontend/dist/` to `C:\Users\test\Downloads\nginx-1.30.5\html`, publishing `index.html` after its assets.
- Preserve the existing Nginx configuration and process. It must already serve that `html` directory on ports `80` and `443`; configure its Vue history fallback as `try_files $uri $uri/ /index.html` if it is not already present.

## SSH and application configuration

Configure repository Actions secrets:

- `DEPLOY_HOST` (defaults in documentation to `222.112.208.68`)
- `BACKEND_SSH_PORT` (`9015`)
- `FRONTEND_SSH_PORT` (`9115`)
- `DEPLOY_USER` (Windows OpenSSH account with permission to write both deployment directories and manage the backend scheduled task)
- `DEPLOY_PASSWORD`
- `DEPLOY_KNOWN_HOSTS` (pinned host-key entries for both SSH ports)

Use repository variables for non-sensitive build values. `BACKEND_ORIGIN` defaults to `http://222.112.208.68:8000`; `FRONTEND_ORIGIN` should be set to the public site origin, such as `https://example.com` when TLS is configured. Also configure browser-visible Vite settings required by the app. Keep the backend `.env` and database on the server. Before first deployment, create `C:\server01\.env` with production settings and set `FRONTEND_ORIGIN` to the same public frontend origin.

## Server prerequisites

- Windows Server 2016 or later runs Windows PowerShell 5.1 with the NetTCPIP and CIM cmdlets, and Windows OpenSSH Server accepts password authentication from GitHub-hosted Actions runners on ports `9015` and `9115`.
- The configured SSH account has Python 3.10 or later, write access to both supplied paths, and permission to manage scheduled tasks.
- Before its first deployment, any existing process listening on port `8000` must be stopped or already managed by the expected `MoaBackendApi` task.
- The Nginx folder contains `nginx.exe`, `conf/`, `mime.types`, and an existing configuration that serves its `html` directory on ports `80` and `443`.
- Firewall rules allow inbound TCP traffic on SSH ports `9015` and `9115`, web ports `80` and `443`, and backend port `8000` if the API is accessed directly.

## Files in the implementation

- `.github/workflows/deploy-backend.yml`: backend packaging and main-branch deployment.
- `.github/workflows/deploy-frontend.yml`: frontend production build and main-branch deployment.
- `.github/deploy/backend.ps1`: backend extraction, environment preservation, and scheduled-task restart.
- `.github/deploy/frontend.ps1`: safe frontend build extraction and document-root update.
- `.github/DEPLOYMENT.md`: secret and server setup instructions.
