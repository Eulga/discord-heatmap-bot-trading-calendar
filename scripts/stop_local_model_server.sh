#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="${LOCAL_MODEL_LOG_DIR:-$REPO_ROOT/data/logs}"
PID_FILE="${LOCAL_MODEL_PID_FILE:-$LOG_DIR/local-model-server.pid}"
LOG_FILE="${LOCAL_MODEL_LOG_FILE:-$LOG_DIR/local-model-server.log}"
LLAMA_SERVER="${LLAMA_SERVER:-/Users/jaeik/llama.cpp/build/bin/llama-server}"
PORT="${LOCAL_MODEL_PORT:-8081}"
WAIT_SECONDS="${LOCAL_MODEL_STOP_WAIT_SECONDS:-20}"
FORCE=false

if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--force]" >&2
  exit 2
fi

is_running_pid() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

is_llama_server_pid() {
  local pid="$1"
  lsof -nP -p "$pid" 2>/dev/null | grep -F "$LLAMA_SERVER" >/dev/null 2>&1
}

pid=""
if [[ -f "$PID_FILE" ]]; then
  pid="$(tr -d '[:space:]' < "$PID_FILE")"
fi

if [[ -z "$pid" ]] && command -v lsof >/dev/null 2>&1; then
  candidate_pid="$(lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -n "$candidate_pid" ]] && is_llama_server_pid "$candidate_pid"; then
    pid="$candidate_pid"
  fi
fi

if [[ -z "$pid" ]]; then
  echo "no managed local model server pid found"
  rm -f "$PID_FILE"
  exit 0
fi

if ! is_running_pid "$pid"; then
  echo "local model server pid is not running: pid=$pid"
  rm -f "$PID_FILE"
  exit 0
fi

if ! is_llama_server_pid "$pid"; then
  echo "refusing to stop non-llama-server process: pid=$pid pid_file=$PID_FILE" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"
{
  echo
  echo "==== $(date '+%Y-%m-%d %H:%M:%S %z') stopping local model server pid=$pid ===="
} >> "$LOG_FILE"

kill "$pid"
for _ in $(seq 1 "$WAIT_SECONDS"); do
  if ! is_running_pid "$pid"; then
    rm -f "$PID_FILE"
    echo "local model server stopped: pid=$pid"
    exit 0
  fi
  sleep 1
done

if [[ "$FORCE" == true ]]; then
  kill -9 "$pid"
  rm -f "$PID_FILE"
  echo "local model server force-stopped: pid=$pid"
  exit 0
fi

echo "local model server did not stop within ${WAIT_SECONDS}s; rerun with --force if needed" >&2
exit 1
