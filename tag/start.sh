#!/bin/bash
# Start Sophon-Realtime-32B-Tag on ONE GPU (80 GB: H100 / H800 / A100 80G).
# usage: bash start.sh        env: GPU=0  PORT=8000  MODEL_DIR=./model  MPS=1  TRT=auto
# several GPUs: one instance per GPU, e.g. GPU=0 PORT=8000 bash start.sh; GPU=1 PORT=8001 bash start.sh  (put a load balancer in front)
# endpoints: ws://HOST:PORT/v1/realtime (full duplex)   http://HOST:PORT/v1/chat/completions (audio in -> text + audio out)
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"; mkdir -p logs
GPU=${GPU:-0}; PORT=${PORT:-8000}; PY=$HERE/.venv/bin; MODEL_DIR=${MODEL_DIR:-$HERE/model}
[ -f logs/server_$PORT.pid ] && PORT=$PORT bash stop.sh >/dev/null 2>&1
DEV=$GPU
case "$GPU" in *,*) MPS=0;; esac
CONFIG=${CONFIG:-sophon_realtime_tag_1gpu.yaml}
if [ "${MPS:-1}" = 1 ] && command -v nvidia-cuda-mps-control >/dev/null; then   # the three stages share the GPU concurrently (much better first-audio under load)
  export CUDA_MPS_PIPE_DIRECTORY=$HERE/.mps/gpu$GPU/pipe CUDA_MPS_LOG_DIRECTORY=$HERE/.mps/gpu$GPU/log; mkdir -p $CUDA_MPS_PIPE_DIRECTORY $CUDA_MPS_LOG_DIRECTORY
  echo get_server_list | nvidia-cuda-mps-control >/dev/null 2>&1 || CUDA_VISIBLE_DEVICES=$GPU nvidia-cuda-mps-control -d
  if echo get_server_list | nvidia-cuda-mps-control >/dev/null 2>&1; then DEV=0; echo "MPS on (GPU $GPU)"; else unset CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY; echo "MPS not available; running without it"; fi
fi
TRT=${TRT:-auto}; [ "$TRT" = auto ] && { $PY/python -c "import tensorrt" 2>/dev/null && TRT=1 || TRT=0; }
[ "$TRT" = 0 ] && echo "WARNING: TensorRT is off (not installed?): the voice runs in plain PyTorch, about 3x slower under load. Re-run install.sh without NO_TRT=1."
sed "s#__HERE__#$HERE#g" config/$CONFIG > logs/deploy_$PORT.yaml
# tag-tts v1.3: distilled flow, 4 steps, no CFG; several requests' flow chunks share one TensorRT call
export SOPHON_FLOW_STEPS=${SOPHON_FLOW_STEPS:-4} SOPHON_FLOW_CFG=${SOPHON_FLOW_CFG:-0} SOPHON_FLOW_ONNX=${SOPHON_FLOW_ONNX:-$MODEL_DIR/talker/flow.decoder.estimator.fp32.onnx} COSYVOICE3_BATCH_FLOW=${COSYVOICE3_BATCH_FLOW:-1} SOPHON_FLOW_MAXB=${SOPHON_FLOW_MAXB:-16}
SOPHON_MODEL=$MODEL_DIR SOPHON_PORT=$PORT SOPHON_BRIDGE_PORT=${SOPHON_BRIDGE_PORT:-$((PORT+700))} VLLM_DISABLE_COMPILE_CACHE=1 COSYVOICE3_TRT=$TRT CUDA_VISIBLE_DEVICES=$DEV PATH=$PY:$PATH \
  setsid nohup $PY/vllm serve $MODEL_DIR --omni --port $PORT --trust-remote-code --init-timeout 3000 --stage-init-timeout 3000 --deploy-config logs/deploy_$PORT.yaml > logs/server_$PORT.log 2>&1 < /dev/null &
echo $! > logs/server_$PORT.pid
echo "starting (first start builds kernels / TensorRT engine: 5-10 min) ... log: logs/server_$PORT.log"
for i in $(seq 1 240); do
  curl -sf -m2 localhost:$PORT/health >/dev/null && break
  kill -0 $(cat logs/server_$PORT.pid) 2>/dev/null || { echo "server exited — see logs/server_$PORT.log"; tail -20 logs/server_$PORT.log; exit 1; }
  sleep 5
done
curl -sf -m2 localhost:$PORT/health >/dev/null || { echo "timeout — see logs/server_$PORT.log"; exit 1; }
echo "warming up ..."; $PY/python client_example.py --url http://127.0.0.1:$PORT --quiet >/dev/null 2>&1
echo "READY  ws://127.0.0.1:$PORT/v1/realtime   http://127.0.0.1:$PORT/v1/chat/completions   (web demo: python client_example.py)"
