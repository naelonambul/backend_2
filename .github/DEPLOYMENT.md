# Windows server deployment

The backend and frontend deploy independently when their files are pushed to `main` (including a pull request merge). The backend workflow transfers `app/` and `requirements.txt`; the frontend workflow builds Vite's production output and transfers only `dist/`. Neither workflow runs pytest or Jest. The existing `test.yml` workflow is not part of deployment.

The server receives files over Windows OpenSSH/SCP. It does not need a GitHub repository credential or Node.js. Both workflows use the same host and Windows account, with a separate SSH port for each deployment.

## Repository Actions secrets

In **Settings → Secrets and variables → Actions**, add these repository secrets:

| Secret | Value |
| --- | --- |
| `DEPLOY_HOST` | `222.112.208.68` |
| `BACKEND_SSH_PORT` | `9015` |
| `FRONTEND_SSH_PORT` | `9115` |
| `DEPLOY_USER` | Windows account name accepted by OpenSSH, for example `test`. |
| `DEPLOY_PASSWORD` | Password for that Windows account. |
| `DEPLOY_KNOWN_HOSTS` | Verified SSH host-key lines for both ports. |

Create the host-key entries from a trusted machine with `ssh-keyscan -p 9015 222.112.208.68` and `ssh-keyscan -p 9115 222.112.208.68`. Verify each fingerprint against the server before saving both output lines in `DEPLOY_KNOWN_HOSTS`. The workflows require strict host-key checking and do not discover or accept host keys during deployment.

## Optional Actions variables

Add these under **Settings → Secrets and variables → Actions → Variables** when the defaults do not fit production:

| Variable | Default / purpose |
| --- | --- |
| `BACKEND_ORIGIN` | Defaults to `https://api.nenene.n-e.kr`; compiled into the frontend as its API origin. |
| `FRONTEND_ORIGIN` | Defaults to `http://222.112.208.68`. Set to the actual public site origin, such as `https://example.com`, when TLS/domain routing is configured. |
| `VITE_KAKAO_JAVASCRIPT_KEY` | Browser-visible Kakao JavaScript key for production. |
| `VITE_KAKAO_REDIRECT_URI` | Defaults to `<FRONTEND_ORIGIN>/auth/kakao/callback`. Register this URI with Kakao. |
| `VITE_PORTONE_STORE_ID` | Browser-visible PortOne store ID. |
| `VITE_PORTONE_CHANNEL_KEY` | Browser-visible PortOne channel key. |

The frontend workflow builds with Node.js and runs `npm ci` followed by `npm run build`. It does not run Jest.

## Windows server preparation

1. Use Windows Server 2016 or later with Windows PowerShell 5.1, the NetTCPIP and CIM cmdlets, and Windows OpenSSH Server. Configure OpenSSH to accept password authentication from GitHub-hosted Actions runners on port `9015` for backend deployment and port `9115` for frontend deployment. Both ports may be listeners on the same server/account.
2. Install Python 3.10 or later and make `python.exe` available in the deployment account's PATH. Each deployment installs requirements into an isolated versioned environment before switching the managed backend task.
3. Ensure `C:\server01` exists. Before the first backend deployment, create `C:\server01\.env` with production settings, including a strong `SECRET_KEY`, the live database URL, payment credentials, and `FRONTEND_ORIGIN` set to the actual public site origin.
4. Keep the SQLite database at `C:\server01\app.db`. The workflow never packages or replaces `.env` or `app.db`.
5. Ensure `C:\Users\test\Downloads\nginx-1.30.5` contains `nginx.exe`, `conf\`, and `mime.types`; its `html` directory must be the document root used by the existing Nginx configuration.
6. Before the first deployment, stop any existing process or supervisor listening on port `8000`, unless it is already the `MoaBackendApi` task using the expected Python/Uvicorn command. The script refuses to deploy over an unmanaged listener so it cannot mistake the old server's response for the new one.
7. Grant the SSH account permission to write to `C:\server01` and the Nginx install directory, inspect TCP listeners and processes, and create/manage scheduled tasks and run as a batch job for the backend. The backend script registers `MoaBackendApi` to start at Windows startup. It switches to the new isolated Python environment only after dependencies install, then waits for HTTP 200 from `http://127.0.0.1:8000/`; a failed startup restores the previous app and task. If the first deployment fails, it removes the newly registered task before deleting its environment.
8. Keep the existing Nginx configuration that serves ports `80` and `443`. It must serve the supplied `html` directory and should contain `try_files $uri $uri/ /index.html` for Vue history routes. The frontend deployment updates files only; it does not replace Nginx configuration or restart Nginx.
9. Allow inbound TCP traffic on SSH ports `9015` and `9115`, Nginx ports `80` and `443`, and backend port `8000` if the API is accessed directly by browsers.

The backend task runs `uvicorn app.main:app` from `C:\server01` on `0.0.0.0:8000`. Nginx continues serving the updated static files through its existing HTTP/HTTPS listeners.

## Workflow triggers

- `deploy-backend.yml` runs on `main` when `app/**`, `requirements.txt`, or its deployment files change. It connects through `BACKEND_SSH_PORT`.
- `deploy-frontend.yml` runs on `main` when `frontend/**` or its deployment files change. It connects through `FRONTEND_SSH_PORT`.
- Both workflows also support manual runs, restricted to the `main` ref.

The SSH ports are independently configurable through `BACKEND_SSH_PORT` and `FRONTEND_SSH_PORT`. Application ports remain FastAPI `8000` and Nginx `80`/`443`.
