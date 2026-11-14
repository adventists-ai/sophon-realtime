#!/bin/bash
# Sophon Realtime for Mac (Apple Silicon, MLX) -- one-command install.
#   bash install.sh            # auto-detects whether Hugging Face is reachable; otherwise uses ModelScope + mirrors (mainland China)
#   SOPHON_HOME=/path bash install.sh   # install somewhere other than ~/sophon-mac
#   SOPHON_SRC=hf|ms bash install.sh    # force the weight source
set -euo pipefail
H="${SOPHON_HOME:-$HOME/sophon-mac}"; HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_HF="adventists-ai/Sophon-Realtime-32B-Flash-4bit-MLX"; REPO_MS="AdventistsAI/Sophon-Realtime-32B-Flash-4bit-MLX"
say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# --- checks -------------------------------------------------------------------------------------------------------------------------
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || die "needs a Mac with Apple silicon (M1 or later)."
MAJ=$(sw_vers -productVersion | cut -d. -f1); [ "$MAJ" -ge 14 ] || die "needs macOS 14 or later."
MEM=$(( $(sysctl -n hw.memsize) / 1073741824 ))
[ "$MEM" -ge 32 ] || die "needs at least 32 GB of unified memory (this Mac has ${MEM} GB). The model uses about 26 GB while talking."
[ "$MEM" -ge 36 ] || echo "Note: ${MEM} GB works but is tight; close other apps before starting. 36 GB or more is recommended."
mkdir -p "$H"; FREE=$(df -g "$H" | awk 'NR==2{print $4}')
[ "$FREE" -ge 30 ] || die "needs about 30 GB of free disk (the model is ~24 GB); ${FREE} GB free at $H."

SRC="${SOPHON_SRC:-}"
if [ -z "$SRC" ]; then curl -s -m 6 -o /dev/null https://huggingface.co && SRC=hf || SRC=ms; fi
if [ "$SRC" = ms ]; then
  export UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple" PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
  echo "Using ModelScope and the Tsinghua PyPI mirror."
fi

# --- python environment ----------------------------------------------------------------------------------------------------------------
say "Python environment"
UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
  if /usr/bin/python3 -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
    /usr/bin/python3 -m venv "$H/.boot" && "$H/.boot/bin/pip" install -q uv && UV="$H/.boot/bin/uv"
  else
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$H/.boot/bin" INSTALLER_NO_MODIFY_PATH=1 sh && UV="$H/.boot/bin/uv"
  fi
fi
[ -x "$UV" ] || die "could not install uv."
[ -x "$H/.venv/bin/python" ] || "$UV" venv -q --python 3.12 "$H/.venv"
"$UV" pip install -q --python "$H/.venv/bin/python" "mlx>=0.29" "mlx-lm>=0.28" "mlx-audio==0.6.5" livekit sounddevice soundfile scipy numpy websockets \
  "transformers>=4.57" huggingface_hub modelscope

# --- code ------------------------------------------------------------------------------------------------------------------------------
say "Program files"
mkdir -p "$H/app"
for f in engine.py mlx_ear.py aec.py live.py serve.py system_prompt.json; do rm -f "$H/app/$f"; cp "$HERE/$f" "$H/app/$f"; chmod 644 "$H/app/$f"; done
cat > "$H/sophon" <<EOS
#!/bin/bash
exec "$H/.venv/bin/python" "$H/app/live.py" "\$@"
EOS
cat > "$H/sophon-serve" <<EOS
#!/bin/bash
exec "$H/.venv/bin/python" "$H/app/serve.py" "\$@"
EOS
chmod +x "$H/sophon" "$H/sophon-serve"

# --- weights ---------------------------------------------------------------------------------------------------------------------------
# Sophon-Realtime-32B-Flash-4bit-MLX = the Flash-4bit weights repacked for MLX (bit-identical). convert.py does the same from the CUDA repo.
if [ ! -f "$H/models/thinker_mlx/model.safetensors.index.json" ] || [ ! -f "$H/models/.complete" ]; then
  say "Downloading the model (~24 GB, once; run again to resume if interrupted)"
  mkdir -p "$H/models"
  if [ "$SRC" = hf ]; then
    "$H/.venv/bin/hf" download "$REPO_HF" --local-dir "$H/models" || die "download failed; run the installer again to resume."
  else
    "$H/.venv/bin/modelscope" download --model "$REPO_MS" --local_dir "$H/models" || die "download failed; run the installer again to resume."
  fi
  touch "$H/models/.complete"
fi

say "Done."
echo "Start talking:   $H/sophon            (Chinese)"
echo "                 $H/sophon --lang en  (English)"
echo "A microphone is needed (a Mac Studio / mini has none built in). Echo cancellation is on, so speakers are fine; with a headset you can add --no-aec."
