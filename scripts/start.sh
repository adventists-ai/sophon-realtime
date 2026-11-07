#!/usr/bin/env bash
# Start Sophon-Realtime v1 (Expressive): thinker (vLLM) + speaking engine + gateway with the web demo.
# usage: SOPHON_MODEL_DIR=/path/to/Sophon-Realtime-v1 [THINKER_GPU=0 TALKER_GPU=1 PORT=8000] bash scripts/start.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
: "${SOPHON_MODEL_DIR:?set SOPHON_MODEL_DIR to the downloaded Sophon-Realtime-v1 directory}"
THINKER_GPU=${THINKER_GPU:-0}; TALKER_GPU=${TALKER_GPU:-1}; PORT=${PORT:-8000}
THINKER_PORT=${THINKER_PORT:-8300}; TALKER_PORT=${TALKER_PORT:-8120}
THINKER_ENV=${THINKER_ENV:-$HERE/.venv-thinker}; ENGINE_ENV=${ENGINE_ENV:-$HERE/.venv-engine}
REPLY_LORA=${SOPHON_REPLY_LORA:-$SOPHON_MODEL_DIR/adapters/tag}
LORA_RANK=${LORA_RANK:-16}
LOG=${LOG_DIR:-$HERE/logs}; mkdir -p "$LOG"
export SOPHON_MODEL_DIR PYTHONPATH="$HERE${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/3] thinker on GPU $THINKER_GPU (port $THINKER_PORT)"
CUDA_VISIBLE_DEVICES=$THINKER_GPU PATH="$THINKER_ENV/bin:$PATH" nohup "$THINKER_ENV/bin/vllm" serve "$SOPHON_MODEL_DIR/base" \
  --served-model-name dj --enable-lora --lora-modules sophon="$REPLY_LORA" --max-lora-rank "$LORA_RANK" \
  --quantization fp8 --max-model-len 8192 --gpu-memory-utilization ${THINKER_MEM:-0.85} --port "$THINKER_PORT" \
  > "$LOG/thinker.log" 2>&1 < /dev/null & echo $! > "$LOG/thinker.pid"

echo "[2/3] speaking engine on GPU $TALKER_GPU (port $TALKER_PORT)"
CUDA_VISIBLE_DEVICES=$TALKER_GPU OMP_NUM_THREADS=${OMP_NUM_THREADS:-8} PYTHONUNBUFFERED=1 nohup "$ENGINE_ENV/bin/python" -m sophon_expressive.talker_server \
  --port "$TALKER_PORT" > "$LOG/talker.log" 2>&1 < /dev/null & echo $! > "$LOG/talker.pid"

wait_for() {  # url, name, log
  for i in $(seq 1 180); do
    if curl -sf "$1" > /dev/null 2>&1; then echo "  $2 ready"; return 0; fi
    if ! kill -0 "$(cat "$3")" 2>/dev/null; then echo "  $2 exited, see ${3%.pid}.log"; exit 1; fi
    sleep 5
  done; echo "  $2 not ready after 15 min, see ${3%.pid}.log"; exit 1
}
wait_for "http://127.0.0.1:$THINKER_PORT/v1/models" thinker "$LOG/thinker.pid"
wait_for "http://127.0.0.1:$TALKER_PORT/health" "speaking engine" "$LOG/talker.pid"

echo "[3/3] gateway + web demo on port $PORT"
PYTHONUNBUFFERED=1 nohup "${GATEWAY_ENV:-$ENGINE_ENV}/bin/python" -m sophon_expressive.gateway --port "$PORT" \
  --dj "http://127.0.0.1:$THINKER_PORT" --talker32 "http://127.0.0.1:$TALKER_PORT" > "$LOG/gateway.log" 2>&1 < /dev/null & echo $! > "$LOG/gateway.pid"
sleep 3
echo "Open http://<this machine>:$PORT/  (WebSocket: ws://<this machine>:$PORT/ws)"
