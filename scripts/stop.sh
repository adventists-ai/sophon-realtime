#!/usr/bin/env bash
# Stop the services started by scripts/start.sh
HERE=$(cd "$(dirname "$0")/.." && pwd); LOG=${LOG_DIR:-$HERE/logs}
for n in gateway talker thinker; do
  f="$LOG/$n.pid"
  if [ -f "$f" ]; then
    p=$(cat "$f"); kill "$p" 2>/dev/null && echo "stopped $n ($p)"; pkill -P "$p" 2>/dev/null; rm -f "$f"
  fi
done
