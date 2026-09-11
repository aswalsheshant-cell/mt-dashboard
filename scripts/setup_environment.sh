#!/bin/bash
# Provision Python dependencies for this repo.
#
# This belongs in the ENVIRONMENT SETUP step, not in the SessionStart hook.
# Setup runs when a VM is provisioned and its result is cached; the session
# hook runs on every resume and must stay fast. A pip install on every resume
# would cost seconds and could fail on a flaky network, taking the session
# with it.
#
# Idempotent, non-interactive, and safe to run repeatedly: already-satisfied
# packages are skipped by pip.
set -uo pipefail
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_ROOT"

echo "=== mt-dashboard: Python dependency setup ==="
if [ ! -f requirements.txt ]; then
  echo "No requirements.txt -- nothing to install."; exit 0
fi

# Node is handled by .claude/hooks/session-start.sh; browsers are provisioned
# by the environment. This step is Python only.
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

if python3 -m pip install -q -r requirements.txt; then
  echo "Python dependencies installed from requirements.txt."
else
  echo "WARNING: pip install did not complete. The session still works, but the" >&2
  echo "pytest-based tests will not run. Re-run this script when the network allows." >&2
  exit 0          # never fail provisioning over this
fi

python3 - <<'PY'
import importlib.util
missing = [m for m in ("pandas", "pytest", "openpyxl", "pyxlsb")
           if importlib.util.find_spec(m) is None]
print("All expected modules present." if not missing
      else "Still missing: " + ", ".join(missing))
PY
echo "=== setup complete ==="
