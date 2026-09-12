#!/bin/bash
# PostToolUse(Write) hook: note when a .pptx file is written.
#
# This checks the written file's EXTENSION ONLY. It does not open, render, or
# otherwise validate the deck's content -- never print a message claiming
# "validated" or "presentation-ready" here, since no such check runs.
#
# The hook payload arrives as JSON on stdin (never as $1 or an env var) --
# see https://code.claude.com/docs/en/hooks.md. Parse it defensively so a
# malformed or missing payload can never fail this hook.
set -euo pipefail

PAYLOAD="$(timeout 2 cat 2>/dev/null || true)"
[ -z "$PAYLOAD" ] && exit 0

FILE_PATH="$(printf '%s' "$PAYLOAD" | python3 -c \
  'import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_input", {}).get("file_path") or d.get("tool_response", {}).get("filePath") or "")
except Exception:
    print("")' 2>/dev/null || true)"

case "$FILE_PATH" in
  *.pptx)
    printf '{"systemMessage":"PPTX file written: %s (extension match only -- no content validation was run)."}\n' "$FILE_PATH"
    ;;
esac
exit 0
