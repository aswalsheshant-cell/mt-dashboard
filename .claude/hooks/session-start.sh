#!/bin/bash
set -euo pipefail

cd "$CLAUDE_PROJECT_DIR"

echo "=== mt-dashboard session setup ==="

if [ -f package-lock.json ]; then
  echo "package-lock.json found -- installing Node dependencies (npm install)..."
  npm install
elif [ -f package.json ]; then
  echo "package.json found (no lockfile) -- running npm install..."
  npm install
else
  echo "No Node project manifest found -- skipping npm setup."
fi

echo "=== Environment ready ==="
