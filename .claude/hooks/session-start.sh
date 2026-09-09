#!/bin/bash
# SessionStart hook: restore Node dependencies only when actually needed.
#
# Design goals (see CLAUDE.md "Cloud Session Restart Resilience"):
#   - deterministic: use the committed lockfile via `npm ci` when repair is
#     needed, never `npm install` over an existing lockfile (that can drift
#     package-lock.json instead of respecting it)
#   - fast on a warm/resumed container: skip installation entirely when
#     node_modules already satisfies package.json
#   - no network/Git side effects when the environment is already healthy
#   - never touches Git, never commits/pushes, never prints secrets
set -euo pipefail

# Never let a dependency restore trigger a Playwright browser download here --
# browsers are provisioned separately by the environment (see CLAUDE.md /
# session docs); this hook's job is Node package resolution only.
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Locate repo root without assuming a machine-specific absolute path.
REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_ROOT"

echo "=== mt-dashboard session setup ==="

if [ ! -f package.json ]; then
  echo "No package.json -- nothing to restore."
  exit 0
fi

# Healthy check: node_modules exists and satisfies package.json's dependency
# tree. `npm ls --depth=0` is a local resolution check (no network call) and
# exits non-zero on missing/invalid/extraneous top-level packages.
if [ -d node_modules ] && npm ls --depth=0 >/dev/null 2>&1; then
  echo "Dependencies already present and valid -- skipping install."
  exit 0
fi

echo "Dependencies missing or invalid -- restoring..."

if [ -f package-lock.json ]; then
  echo "package-lock.json found -- running 'npm ci' for a deterministic, clean install."
  if ! npm ci; then
    echo "ERROR: 'npm ci' failed to restore dependencies from package-lock.json." >&2
    exit 1
  fi
else
  echo "No package-lock.json -- running 'npm install' (no lockfile to pin against)."
  if ! npm install; then
    echo "ERROR: 'npm install' failed to restore dependencies." >&2
    exit 1
  fi
fi

echo "=== Environment ready ==="
