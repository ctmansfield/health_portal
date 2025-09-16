#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-/repos/health_portal}"
PROFILE="${2:-local}"

if [[ ! -d "$REPO/.git" ]]; then
  echo "Repo not found or not a git repo: $REPO" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/gen_runtime.py" "$REPO" "$PROFILE"

echo "Generated configs for profile: $PROFILE"
echo " - $REPO/.env.local"
echo " - $REPO/src/config/runtime.generated.json"
echo " - $REPO/public/runtime-config.json (optional)"
