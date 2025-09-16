#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-/repos/health_portal}"

read -r -p "Remove multi-backend files (working tree only)? (y/N) " ans
[[ "${ans,,}" == "y" ]] || { echo "Aborted."; exit 0; }

rm -f "$REPO/config/backends.json"
rm -rf "$REPO/tools/multibackend"
rm -f "$REPO/src/config/runtime.generated.json" || true
rm -f "$REPO/public/runtime-config.json" || true
rm -f "$REPO/.env.local" || true

echo "Removed. Commit deletions as needed."
