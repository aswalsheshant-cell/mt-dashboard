#!/bin/bash
# Diagnostic-only environment report. Read-only: changes nothing, installs
# nothing, and prints no confidential value.
#
# Written for the SessionStart hook, so it must stay fast (well under a second)
# and must never fail the session -- every probe degrades to "unknown" rather
# than exiting non-zero.
#
# What it deliberately does NOT print: employee names, employee IDs, DMS client
# names, incentive amounts, or the contents of any restricted input. Presence
# is reported as a count, never as data.
set -uo pipefail

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_ROOT" 2>/dev/null || exit 0
VERBOSE="${1:-}"

say() { printf '  %-22s %s\n' "$1" "$2"; }

echo "--- environment ---"
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then MODE="cloud (managed VM)"; else MODE="local"; fi
say "mode" "$MODE"
say "uptime" "$(uptime -p 2>/dev/null || echo unknown)"

# Resource pressure. These are the numbers that separate "idle reclaim"
# (expected, harmless) from "the container is being killed under load".
AVAIL_MEM=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}')
TOTAL_MEM=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')
AVAIL_DISK=$(df -Pm . 2>/dev/null | awk 'NR==2{print $4}')
DISK_PCT=$(df -P . 2>/dev/null | awk 'NR==2{print $5}')
say "memory" "${AVAIL_MEM:-?} MB free of ${TOTAL_MEM:-?} MB"
say "disk" "${AVAIL_DISK:-?} MB free (${DISK_PCT:-?} used)"
say "cpus" "$(nproc 2>/dev/null || echo '?')"
[ -n "${AVAIL_MEM:-}" ] && [ "$AVAIL_MEM" -lt 1024 ] && echo "  ** LOW MEMORY — investigate before heavy builds"
[ -n "${AVAIL_DISK:-}" ] && [ "$AVAIL_DISK" -lt 2048 ] && echo "  ** LOW DISK — clear build artifacts before writing data.js"

echo "--- repo ---"
say "branch" "$(git branch --show-current 2>/dev/null || echo '?')"
say "HEAD" "$(git log --oneline -1 2>/dev/null || echo '?')"
DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
say "working tree" "$([ "$DIRTY" = "0" ] && echo clean || echo "$DIRTY uncommitted file(s)")"
UP=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)
if [ -n "$UP" ]; then
  say "vs $UP" "$(git rev-list --left-right --count "$UP"...HEAD 2>/dev/null | awk '{print $1" behind, "$2" ahead"}')"
else
  say "upstream" "not pushed yet"
fi

echo "--- toolchain ---"
say "python" "$(python3 --version 2>&1 | head -1)"
say "node" "$(node --version 2>/dev/null || echo 'absent')"
# The session hook validates dependencies itself; skip the ~1s npm probe when
# it has already run, so the hook stays fast on resume.
if [ "${SKIP_NPM_PROBE:-0}" = "1" ]; then
  say "node_modules" "$([ -d node_modules ] && echo 'present (checked by hook)' || echo MISSING)"
else
  say "node_modules" "$([ -d node_modules ] && npm ls --depth=0 >/dev/null 2>&1 && echo 'present and valid' || echo 'MISSING OR INVALID — session hook will restore')"
fi
say "pandas" "$(python3 -c 'import pandas;print(pandas.__version__)' 2>/dev/null || echo 'absent — pip install pandas before a data build')"
say "chromium" "$([ -x /opt/pw-browsers/chromium ] && echo present || echo absent)"

echo "--- project assets ---"
say "dashboard/data.js" "$([ -f dashboard/data.js ] && echo "$(du -h dashboard/data.js | cut -f1)" || echo MISSING)"
say "config" "$([ -f config/analytics_config.json ] && echo present || echo MISSING)"
say "project state" "$([ -f docs/PROJECT_STATE.md ] && echo present || echo 'MISSING — run the state update')"

# Restricted inputs: presence only. A resumed environment may not have them,
# and nothing may be reconstructed from memory when they are gone.
echo "--- restricted inputs (presence only, never contents) ---"
N_DMS=$(ls /tmp/massit_in/*.csv 2>/dev/null | wc -l | tr -d ' ')
say "DMS extracts staged" "${N_DMS} file(s)$([ "$N_DMS" = "0" ] && echo ' — incentive ingest BLOCKED until re-supplied')"
say "incentive working" "$([ -d incentive_working ] && echo "$(ls incentive_working 2>/dev/null | wc -l | tr -d ' ') file(s), gitignored" || echo 'absent — regenerate from source when needed')"

echo "--- background processes ---"
# Test whether the PORT is listening, not whether a process command line
# contains the string -- `pgrep -f` also matches the shell running this check,
# which reports a stale server that does not exist.
if command -v ss >/dev/null 2>&1; then
  LISTEN=$(ss -ltnH 2>/dev/null | grep -c ':8899 ')
else
  LISTEN=$(python3 - <<'PY' 2>/dev/null || echo 0
import socket
s = socket.socket()
s.settimeout(0.3)
print(0 if s.connect_ex(("127.0.0.1", 8899)) else 1)
PY
)
fi
say "test server :8899" "$([ "${LISTEN:-0}" = "0" ] && echo 'not running' || echo 'STILL RUNNING — stop it before re-running the sweep')"

if [ "$VERBOSE" = "--verbose" ]; then
  echo "--- top memory consumers ---"
  ps -eo pmem,rss,comm --sort=-pmem 2>/dev/null | head -6 | sed 's/^/  /'
fi
exit 0
