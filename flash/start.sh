#!/bin/bash
# Start Sophon-Realtime-32B-Flash on ONE GPU (80 GB: H100 / H800 / A100 80G).
# usage: bash start.sh        env: GPU=0  PORT=8000  MPS=0
# several GPUs: one instance per GPU, e.g. GPU=0 PORT=8000 bash start.sh; GPU=1 PORT=8001 bash start.sh  (put a load balancer in front)
# endpoints: ws://HOST:PORT/v1/realtime (full duplex)   http://HOST:PORT/v1/chat/completions (audio in -> text + audio out)
HERE=$(cd "$(dirname "$0")" && pwd); cd "$HERE"; mkdir -p logs
GPU=${GPU:-0}; PORT=${PORT:-8000}; PY=$HERE/.venv/bin
[ -f logs/server_$PORT.pid ] && PORT=$PORT bash stop.sh >/dev/null 2>&1
DEV=$GPU
CONFIG=${CONFIG:-sophon_realtime_flash_1gpu.yaml}
# vLLM compiles a few kernels at the first start (several minutes) and caches them. Keep the cache with this install: the default
# cache in ~/.cache is shared by every vLLM install of the user, and installs with different paths rebuild it at each start.
export FLASHINFER_WORKSPACE_BASE=${FLASHINFER_WORKSPACE_BASE:-$HERE}
if [ "${MPS:-0}" = 1 ] && command -v nvidia-cuda-mps-control >/dev/null; then   # optional: the three stages share the GPU through MPS
  export CUDA_MPS_PIPE_DIRECTORY=$HERE/.mps/gpu$GPU/pipe CUDA_MPS_LOG_DIRECTORY=$HERE/.mps/gpu$GPU/log; mkdir -p $CUDA_MPS_PIPE_DIRECTORY $CUDA_MPS_LOG_DIRECTORY
  echo get_server_list | nvidia-cuda-mps-control >/dev/null 2>&1 || CUDA_VISIBLE_DEVICES=$GPU nvidia-cuda-mps-control -d
  if echo get_server_list | nvidia-cuda-mps-control >/dev/null 2>&1; then DEV=0; echo "MPS on (GPU $GPU)"; else unset CUDA_MPS_PIPE_DIRECTORY CUDA_MPS_LOG_DIRECTORY; fi
fi
sed "s#__HERE__#$HERE#g" config/$CONFIG > logs/deploy_$PORT.yaml
SOPHON_MODEL=$HERE/model SOPHON_PORT=$PORT SOPHON_BRIDGE_PORT=${SOPHON_BRIDGE_PORT:-$((PORT+700))} VLLM_DISABLE_COMPILE_CACHE=1 CUDA_VISIBLE_DEVICES=$DEV PATH=$PY:$PATH \
  setsid nohup $PY/vllm serve $HERE/model --omni --port $PORT --trust-remote-code --init-timeout 3000 --stage-init-timeout 3000 --deploy-config logs/deploy_$PORT.yaml > logs/server_$PORT.log 2>&1 < /dev/null &
echo $! > logs/server_$PORT.pid
echo "starting (first start compiles kernels: about 10 min; later 5-8 min) ... log: logs/server_$PORT.log"
for i in $(seq 1 240); do
  curl -sf -m2 localhost:$PORT/health >/dev/null && break
  kill -0 $(cat logs/server_$PORT.pid) 2>/dev/null || { echo "server exited — see logs/server_$PORT.log"; tail -20 logs/server_$PORT.log; exit 1; }
  sleep 5
done
curl -sf -m2 localhost:$PORT/health >/dev/null || { echo "timeout — see logs/server_$PORT.log"; exit 1; }
echo "warming up ..."; $PY/python client_example.py --url http://127.0.0.1:$PORT --quiet >/dev/null 2>&1
echo "READY  ws://127.0.0.1:$PORT/v1/realtime   http://127.0.0.1:$PORT/v1/chat/completions"
