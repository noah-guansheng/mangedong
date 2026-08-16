#!/usr/bin/env bash
# One-click start for the mangedong studio workbench.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
Usage: ./start.sh [--dry-run] [--help]

Starts the mangedong Web workbench (FastAPI + /app).

Optional environment:
  MANGEDONG_HOST              bind host (default 0.0.0.0)
  MANGEDONG_PORT              bind port (default 8000)
  MANGEDONG_SKIP_INSTALL      1 to skip pip install
  MANGEDONG_NO_VENV           1 to use system Python
  MANGEDONG_DATABASE_URL      default sqlite:///./mangedong.db
  MANGEDONG_STORAGE_DIR       default ./mangedong_storage
  MANGEDONG_SECRET_KEY        app secret
  MANGEDONG_TOKENPLAN_API_KEY Token Plan sk-sp- seat key
  PYTHON                      python binary (default python3)
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

HOST="${MANGEDONG_HOST:-0.0.0.0}"
PORT="${MANGEDONG_PORT:-8000}"

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "mangedong workbench http://127.0.0.1:${PORT}/app"
  echo "health http://127.0.0.1:${PORT}/health"
  echo "uvicorn mangedong.api.app:create_app --factory --host ${HOST} --port ${PORT}"
  exit 0
fi

if [[ "${MANGEDONG_NO_VENV:-0}" != "1" ]]; then
  if [[ ! -d "$ROOT/.venv" ]]; then
    echo "creating virtualenv at $ROOT/.venv"
    "$PYTHON_BIN" -m venv "$ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  PYTHON_BIN="python"
fi

if [[ "${MANGEDONG_SKIP_INSTALL:-0}" != "1" ]]; then
  echo "installing mangedong"
  "$PYTHON_BIN" -m pip install -q -e "$ROOT"
fi

export MANGEDONG_DATABASE_URL="${MANGEDONG_DATABASE_URL:-sqlite:///./mangedong.db}"
export MANGEDONG_STORAGE_DIR="${MANGEDONG_STORAGE_DIR:-./mangedong_storage}"
export MANGEDONG_SECRET_KEY="${MANGEDONG_SECRET_KEY:-dev-secret-change-me}"

echo "mangedong 工作台: http://127.0.0.1:${PORT}/app"
echo "健康检查:         http://127.0.0.1:${PORT}/health"
echo "Ctrl+C 停止。内嵌 worker 会在文件库 SQLite 上自动跑；多机请另开 mangedong worker。"

exec "$PYTHON_BIN" -m uvicorn "mangedong.api.app:create_app" --factory --host "$HOST" --port "$PORT"
