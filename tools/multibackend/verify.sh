#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-/repos/health_portal}"
for f in "$REPO/config/backends.json" \
         "$REPO/tools/multibackend/use-backend.sh" \
         "$REPO/tools/multibackend/gen_runtime.py" \
         "$REPO/tools/multibackend/uninstall.sh" \
         "$REPO/docs/project/MULTI_BACKEND.md"
do
  [[ -f "$f" ]] && echo "OK  - $f" || { echo "MISS- $f"; exit 1; }
done
echo "Verification passed."
