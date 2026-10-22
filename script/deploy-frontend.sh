#!/usr/bin/env bash
set -Eeuo pipefail

STAGING_DIR="${1:?Usage: deploy-frontend.sh <staging-dir> <html-dir>}"
HTML_DIR="${2:-/var/www/html/}"
BUILD_DIR="${STAGING_DIR}/frontend/dist"

if [[ "$HTML_DIR" != "/var/www/html" && "$HTML_DIR" != "/var/www/html/" ]]; then
  echo "Unexpected Nginx document root: $HTML_DIR" >&2
  exit 1
fi
HTML_DIR="/var/www/html"

if [[ "$STAGING_DIR" != "/tmp/haben-frontend-deploy" ]]; then
  echo "Unexpected staging directory: $STAGING_DIR" >&2
  exit 1
fi

if [[ ! -f "$BUILD_DIR/index.html" ]]; then
  echo "Staged frontend build not found: $BUILD_DIR/index.html" >&2
  exit 1
fi

if [[ ! -d "$BUILD_DIR/assets" ]]; then
  echo "Staged frontend assets directory not found: $BUILD_DIR/assets" >&2
  exit 1
fi

# Prefer direct writes when the SSH user owns the document root. Otherwise,
# use passwordless sudo if available.
SUDO=()
if (( EUID != 0 )); then
  if [[ -d "$HTML_DIR" && -w "$HTML_DIR" && -x "$HTML_DIR" ]]; then
    : # The SSH user can publish directly.
  elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    SUDO=(sudo -n)
  else
    echo "The SSH user must be able to write to $HTML_DIR directly or have passwordless sudo." >&2
    exit 1
  fi
fi

run_privileged() {
  if ((${#SUDO[@]})); then
    "${SUDO[@]}" "$@"
  else
    "$@"
  fi
}

run_privileged install -d -m 755 "$HTML_DIR"

# Keep Let's Encrypt challenges and Nginx's 50x page while replacing the site.
run_privileged find "$HTML_DIR" -mindepth 1 -maxdepth 1 \
  ! -name .well-known ! -name 50x.html -exec rm -rf -- {} +
run_privileged cp -a "$BUILD_DIR"/. "$HTML_DIR"/

# Nginx needs traversal on directories and read access to static files.
run_privileged find "$HTML_DIR" -type d -exec chmod 755 {} +
run_privileged find "$HTML_DIR" -type f -exec chmod 644 {} +

rm -rf -- "$STAGING_DIR"
echo "Frontend deployed to $HTML_DIR (directories 755, files 644)"
