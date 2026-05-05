#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="${LOCAL_MODEL_LOG_DIR:-$REPO_ROOT/data/logs}"
PID_FILE="${LOCAL_MODEL_PID_FILE:-$LOG_DIR/local-model-server.pid}"
LOG_FILE="${LOCAL_MODEL_LOG_FILE:-$LOG_DIR/local-model-server.log}"

LLAMA_SERVER="${LLAMA_SERVER:-/Users/jaeik/llama.cpp/build/bin/llama-server}"
MODEL="${LOCAL_MODEL_MODEL_PATH:-/Users/jaeik/models/gemma-e4b/gemma-4-E4B-it-Q4_K_M.gguf}"
MODEL_ALIAS="${LOCAL_MODEL_NAME:-gemma-e4b}"
HOST="${LOCAL_MODEL_HOST:-0.0.0.0}"
PORT="${LOCAL_MODEL_PORT:-8081}"
CTX_SIZE="${LOCAL_MODEL_CTX_SIZE:-4096}"
THREADS="${LOCAL_MODEL_THREADS:-8}"
N_GPU_LAYERS="${LOCAL_MODEL_N_GPU_LAYERS:-all}"
FLASH_ATTN="${LOCAL_MODEL_FLASH_ATTN:-auto}"
REASONING="${LOCAL_MODEL_REASONING:-off}"
WAIT_SECONDS="${LOCAL_MODEL_START_WAIT_SECONDS:-60}"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

if [[ ! -x "$LLAMA_SERVER" ]]; then
  echo "llama-server not found or not executable: $LLAMA_SERVER" >&2
  exit 1
fi

if [[ ! -f "$MODEL" ]]; then
  echo "model file not found: $MODEL" >&2
  exit 1
fi

is_running_pid() {
  local pid="$1"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

is_llama_server_pid() {
  local pid="$1"
  lsof -nP -p "$pid" 2>/dev/null | grep -F "$LLAMA_SERVER" >/dev/null 2>&1
}

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(tr -d '[:space:]' < "$PID_FILE")"
  if is_running_pid "$existing_pid"; then
    if ! is_llama_server_pid "$existing_pid"; then
      echo "pid file points to a non-llama-server process: pid=$existing_pid pid_file=$PID_FILE" >&2
      exit 1
    fi
    echo "==== $(date '+%Y-%m-%d %H:%M:%S %z') local model server already running pid=$existing_pid ====" >> "$LOG_FILE"
    echo "local model server already running: pid=$existing_pid pid_file=$PID_FILE"
    exit 0
  fi
  echo "removing stale local model pid file: $PID_FILE"
  rm -f "$PID_FILE"
fi

listen_pid=""
if command -v lsof >/dev/null 2>&1; then
  listen_pid="$(lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
fi

if [[ -n "$listen_pid" ]]; then
  if is_llama_server_pid "$listen_pid"; then
    echo "$listen_pid" > "$PID_FILE"
    echo "==== $(date '+%Y-%m-%d %H:%M:%S %z') adopted existing local model server pid=$listen_pid port=$PORT ====" >> "$LOG_FILE"
    echo "adopted existing local model server: pid=$listen_pid port=$PORT pid_file=$PID_FILE"
    exit 0
  fi
  echo "port $PORT is already in use by pid=$listen_pid; not starting local model server" >&2
  exit 1
fi

{
  echo
  echo "==== $(date '+%Y-%m-%d %H:%M:%S %z') starting local model server ===="
  echo "llama_server=$LLAMA_SERVER"
  echo "model=$MODEL"
  echo "alias=$MODEL_ALIAS host=$HOST port=$PORT ctx_size=$CTX_SIZE threads=$THREADS n_gpu_layers=$N_GPU_LAYERS flash_attn=$FLASH_ATTN reasoning=$REASONING"
} >> "$LOG_FILE"

nohup "$LLAMA_SERVER" \
  --model "$MODEL" \
  --alias "$MODEL_ALIAS" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CTX_SIZE" \
  --threads "$THREADS" \
  --n-gpu-layers "$N_GPU_LAYERS" \
  --flash-attn "$FLASH_ATTN" \
  --reasoning "$REASONING" \
  --no-webui \
  >> "$LOG_FILE" 2>&1 &

pid="$!"
echo "$pid" > "$PID_FILE"

for _ in $(seq 1 "$WAIT_SECONDS"); do
  if ! is_running_pid "$pid"; then
    echo "local model server exited during startup; see $LOG_FILE" >&2
    rm -f "$PID_FILE"
    exit 1
  fi
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "local model server started: pid=$pid port=$PORT log=$LOG_FILE pid_file=$PID_FILE"
    exit 0
  fi
  sleep 1
done

echo "local model server did not begin listening on port $PORT within ${WAIT_SECONDS}s; see $LOG_FILE" >&2
exit 1
