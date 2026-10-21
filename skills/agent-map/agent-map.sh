#!/usr/bin/env bash
# Start (if needed) and open the live agent map. Usage: agent-map.sh [start|stop|status]
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${AGENT_MAP_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"
LOG="${TMPDIR:-/tmp}/agent-map.log"

pid() { lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null || true; }

case "${1:-start}" in
  stop)
    p="$(pid)"
    if [ -n "$p" ]; then kill $p && echo "ok: agent map stopped"; else echo "ok: not running"; fi
    ;;
  status)
    if [ -n "$(pid)" ]; then echo "ok: running at ${URL}"; else echo "not running"; fi
    ;;
  start)
    if [ -z "$(pid)" ]; then
      nohup python3 "${DIR}/server.py" --port "${PORT}" >"${LOG}" 2>&1 &
      for _ in 1 2 3 4 5 6 7 8 9 10; do [ -n "$(pid)" ] && break; sleep 0.3; done
      if [ -z "$(pid)" ]; then echo "FAILED: server did not start, see ${LOG}"; tail -n 20 "${LOG}"; exit 1; fi
      echo "ok: started at ${URL}"
    else
      echo "ok: already running at ${URL}"
    fi
    open "${URL}" 2>/dev/null || xdg-open "${URL}" 2>/dev/null || true
    ;;
  *)
    echo "usage: $0 [start|stop|status]"; exit 2
    ;;
esac
