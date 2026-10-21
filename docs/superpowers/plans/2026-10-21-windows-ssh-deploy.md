# Windows SSH Deployment Plan

**Goal:** On merges to `main`, package the backend or build the frontend, copy the files to the Windows server, then run the backend on port `8000` and publish frontend files through the existing Nginx service on ports `80` and `443`. The backend SSH port is `9015`; the frontend SSH port is `9115`. Deployment workflows do not run tests.

**Architecture:** Separate path-filtered GitHub Actions workflows. The backend workflow transfers `app/` and `requirements.txt`; the frontend workflow builds Vite `dist/`. Remote PowerShell scripts install the backend payload and update the Nginx document root without replacing Nginx configuration.

**Spec:** `docs/superpowers/specs/2026-10-21-windows-ssh-deploy-design.md`

## Fixed deployment settings

- Backend root: `C:\server01`; FastAPI port: `8000`; backend SSH port: `9015`.
- Frontend static root: `C:\Users\test\Downloads\nginx-1.30.5\html`; Nginx ports: `80` and `443`; frontend SSH port: `9115`.
- SSH secrets: `DEPLOY_HOST`, `BACKEND_SSH_PORT`, `FRONTEND_SSH_PORT`, `DEPLOY_USER`, `DEPLOY_PASSWORD`, `DEPLOY_KNOWN_HOSTS`.
- Preserve backend `.env`, `app.db`, and Nginx configuration.
- Do not add pytest/Jest jobs or modify the existing `.github/workflows/test.yml`.

## Task 1: Add the backend remote deployment script

**Files:**
- Create `.github/deploy/backend.ps1`

**Steps:**

1. Accept the uploaded backend archive path and expand it into a temporary staging directory under `C:\server01`.
2. Require Python 3.10 or later. Create a new versioned virtual environment and install requirements there while the current task continues running.
3. Replace only `app/` and `requirements.txt`, preserving `.env` and `app.db`.
4. Register or update `MoaBackendApi` to run the new environment's `python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000` with working directory `C:\server01`, then start it.
5. Refuse to deploy over a port-8000 listener that is not owned by the expected running `MoaBackendApi` task. Wait for HTTP 200 from `http://127.0.0.1:8000/`; on failure, restore the previous app, requirements, and task environment. If this is a failed first deployment, unregister the new task before removing its environment.

## Task 2: Add the frontend deployment script

**Files:**
- Create `.github/deploy/frontend.ps1`

**Steps:**

1. Accept the uploaded `dist` archive and expand it to a staging directory.
2. Copy static assets and other build files to the supplied Nginx `html` directory, publishing `index.html` last so it references files already present.
3. Preserve existing Nginx configuration and process. Do not replace `conf/nginx.conf` or restart Nginx for static file changes.
4. Clean up temporary files and fail the remote command if extraction or copying fails.

## Task 3: Add build-and-deploy workflows and setup documentation

**Files:**
- Create `.github/workflows/deploy-backend.yml`
- Create `.github/workflows/deploy-frontend.yml`
- Create `.github/DEPLOYMENT.md`

**Steps:**

1. Configure each workflow for `push` to `main` with service-specific path filters, workflow dispatch, concurrency control, and minimal repository permissions.
2. In the backend workflow, archive only `app/` and root `requirements.txt`, configure OpenSSH from the shared host/account/password/host-key secrets and `BACKEND_SSH_PORT`, transfer the archive and script, and invoke PowerShell remotely.
3. In the frontend workflow, run `npm ci` and `npm run build` with production `BACKEND_ORIGIN`, archive only `dist/`, configure OpenSSH with `FRONTEND_SSH_PORT`, transfer the archive and script, and invoke PowerShell remotely.
4. Avoid pytest and Jest commands in both workflows. Leave `.github/workflows/test.yml` unchanged.
5. Document secret names, production variables, server prerequisites, first-deploy `.env` setup, permissions, existing Nginx expectations, and required firewall ports.

## Task 4: Review and verify the implementation

1. Review changed files and ensure archives exclude `.env`, `app.db`, tests, and local environments.
2. Check workflow YAML syntax and parse the PowerShell scripts; do not run pytest or Jest.
3. Confirm workflow triggers, service-specific SSH ports, app ports, fixed paths, backend port ownership/readiness/rollback, supported Windows prerequisites, and Nginx configuration preservation match the spec.
4. Review the branch diff, including the existing 30 commits ahead of `main`.
5. Push `codex/windows-ssh-deploy` to `origin` after local static checks and read-only review pass.
