#!/usr/bin/env bash
set -Eeuo pipefail

STAGING_DIR=${1:?Usage: deploy-backend.sh STAGING_DIR BACKEND_DIR [PORT]}
BACKEND_DIR=${2:?Usage: deploy-backend.sh STAGING_DIR BACKEND_DIR [PORT]}
PORT=${3:-443}

# Keep destructive operations limited to the paths approved for this server.
[[ "$STAGING_DIR" == "/tmp/haben-backend-deploy" ]] || {
  echo "Unexpected staging directory: $STAGING_DIR" >&2
  exit 2
}
[[ "$BACKEND_DIR" == "/home/test/server" ]] || {
  echo "Unexpected backend directory: $BACKEND_DIR" >&2
  exit 2
}
[[ "$PORT" =~ ^[0-9]+$ ]] || {
  echo "Invalid backend port: $PORT" >&2
  exit 2
}

APP_SOURCE="$STAGING_DIR/app"
REQUIREMENTS_SOURCE="$STAGING_DIR/requirements.txt"
PYTHON="$BACKEND_DIR/.venv/bin/python"
SSL_CERT="$BACKEND_DIR/ssl/certificate.crt"
SSL_KEY="$BACKEND_DIR/ssl/private.key"
LOG_FILE="$BACKEND_DIR/uvicorn.log"
PID_FILE="$BACKEND_DIR/backend.pid"

if [[ ! -d "$APP_SOURCE" || ! -f "$REQUIREMENTS_SOURCE" ]]; then
  echo "Staged app or requirements.txt not found in $STAGING_DIR" >&2
  exit 1
fi
for required in "$PYTHON" "$BACKEND_DIR/.env" "$BACKEND_DIR/app.db" "$SSL_CERT" "$SSL_KEY"; do
  if [[ ! -e "$required" ]]; then
    echo "Required existing server file is missing: $required" >&2
    exit 1
  fi
done
if [[ -z "${DEPLOY_SUDO_PASSWORD:-}" ]]; then
  echo "DEPLOY_SUDO_PASSWORD was not provided to the deployment step" >&2
  exit 1
fi

sudo_run() {
  printf '%s\n' "$DEPLOY_SUDO_PASSWORD" | sudo -S -p '' -- "$@"
}

# Install dependencies before stopping the live process, reducing downtime.
sudo_run "$PYTHON" -m pip install --disable-pip-version-check -q -r "$REQUIREMENTS_SOURCE"

# Only stop listeners that are clearly this app's Uvicorn process.
listeners=$(sudo_run ss -H -ltnp "sport = :$PORT")
mapfile -t listener_pids < <(grep -oE 'pid=[0-9]+' <<<"$listeners" | cut -d= -f2 | sort -u)
for pid in "${listener_pids[@]}"; do
  command_line=$(sudo_run ps -p "$pid" -o args= || true)
  if [[ "$command_line" != *"$BACKEND_DIR/.venv/bin/uvicorn"* || \
        "$command_line" != *"app.main:app"* || \
        "$command_line" != *"--port $PORT"* ]]; then
    echo "Port $PORT is held by an unexpected process (pid $pid); refusing to stop it." >&2
    exit 1
  fi
  echo "Stopping existing backend process $pid"
  sudo_run kill -TERM "$pid"
done

for _ in {1..30}; do
  listeners=$(sudo_run ss -H -ltnp "sport = :$PORT")
  [[ -z "$listeners" ]] && break
  sleep 1
done
if [[ -n "$listeners" ]]; then
  echo "Port $PORT is still in use after requesting shutdown." >&2
  exit 1
fi

# Replace only application code and its dependency manifest. Runtime state,
# credentials, database, virtual environment, and TLS files remain in place.
sudo_run rm -rf "$BACKEND_DIR/app.next"
sudo_run cp -a "$APP_SOURCE" "$BACKEND_DIR/app.next"
sudo_run rm -rf "$BACKEND_DIR/app"
sudo_run mv "$BACKEND_DIR/app.next" "$BACKEND_DIR/app"
sudo_run install -m 0644 "$REQUIREMENTS_SOURCE" "$BACKEND_DIR/requirements.txt"

# Keep the established detached Uvicorn launch style; no systemd unit is added.
sudo_run bash -c '
  set -e
  cd "$1"
  nohup "$2" -m uvicorn app.main:app --host 0.0.0.0 --port "$3" \
    --ssl-certfile "$4" --ssl-keyfile "$5" >>"$6" 2>&1 </dev/null &
  echo "$!" >"$7"
' _ "$BACKEND_DIR" "$PYTHON" "$PORT" "$SSL_CERT" "$SSL_KEY" "$LOG_FILE" "$PID_FILE"

for _ in {1..30}; do
  if curl --insecure --fail --silent --show-error --max-time 2 \
      "https://127.0.0.1:$PORT/openapi.json" -o /dev/null 2>/dev/null; then
    echo "Backend is responding over HTTPS on port $PORT."
    rm -rf -- "$STAGING_DIR"
    unset DEPLOY_SUDO_PASSWORD
    exit 0
  fi
  sleep 1
done

echo "Backend did not become healthy; recent Uvicorn log follows:" >&2
sudo_run tail -n 50 "$LOG_FILE" >&2 || true
exit 1
