#!/bin/bash
# Run the 11-tab x 4-FY-state dashboard sweep against a throwaway local server.
#
# Owns the server's whole lifecycle: starts it on a free port, records the PID,
# and stops THAT PID on exit -- including on Ctrl-C or failure. Previous runs
# left servers behind and were cleaned up with a broad `pkill -f`, which can
# kill unrelated processes that merely mention the pattern. This kills only
# what it started.
set -uo pipefail
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_ROOT"

PORT="${SWEEP_PORT:-8899}"
SWEEP_JS="${1:-}"
SERVER_PID=""

cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    echo "stopped test server (pid $SERVER_PID)"
  fi
}
trap cleanup EXIT INT TERM

port_busy() {
  python3 - "$PORT" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket(); s.settimeout(0.3)
sys.exit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) else 1)
PY
}

if ! port_busy; then
  echo "ERROR: port $PORT is already in use. Stop that server, or set SWEEP_PORT." >&2
  exit 1
fi

( cd dashboard && exec python3 -m http.server "$PORT" >/dev/null 2>&1 ) &
SERVER_PID=$!

for _ in $(seq 1 10); do
  port_busy || break
  sleep 0.5
done
if port_busy; then
  echo "ERROR: test server did not come up on $PORT." >&2
  exit 1
fi
echo "test server up on :$PORT (pid $SERVER_PID)"

if [ -z "$SWEEP_JS" ] || [ ! -f "$SWEEP_JS" ]; then
  echo "Usage: $0 <path-to-sweep.js>   (SWEEP_PORT=$PORT)" >&2
  exit 2
fi
SWEEP_PORT="$PORT" node "$SWEEP_JS"
RC=$?
exit $RC
