#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"
test -n "$ID" || { echo "usage: $0 <ID>"; exit 2; }
# Try to open both PROMPT and README in existing VS Code window
if command -v code >/dev/null 2>&1; then
  code -r "blocks/active/${ID}/PROMPT.md" "blocks/active/${ID}/README.md" || true
else
  echo "[info] VS Code 'code' CLI not found. Open these manually:"
  echo " - blocks/active/${ID}/PROMPT.md"
  echo " - blocks/active/${ID}/README.md"
fi
