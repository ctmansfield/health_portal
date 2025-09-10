#!/usr/bin/env bash
set -euo pipefail
PATCH_DIR="${1:-}"; [[ -n "$PATCH_DIR" && -d "$PATCH_DIR" ]] || { echo "usage: $0 /path/to/patch_dir"; exit 1; }

# trivial YAML reader (key: value)
yaml_get(){ grep -E "^[[:space:]]*$1:" "$2" | head -n1 | sed -E "s/^[[:space:]]*$1:[[:space:]]*//"; }

PATCH_FILE="$PATCH_DIR/PATCH.yaml"
[[ -f "$PATCH_FILE" ]] || { echo "PATCH.yaml missing"; exit 1; }

TARGET="$(yaml_get target "$PATCH_FILE")"
SERVICE_NAME="$(yaml_get service_name "$PATCH_FILE")"
COMMIT_MSG="$(yaml_get commit_message "$PATCH_FILE")"
[[ -n "$TARGET" && -n "$SERVICE_NAME" ]] || { echo "bad PATCH.yaml"; exit 1; }

echo "[+] install $SERVICE_NAME -> $TARGET"
mkdir -p "$TARGET"
rsync -a --delete --exclude 'PATCH.yaml' --exclude '.DS_Store' "$PATCH_DIR/" "$TARGET/"

# start + verify if scripts exist
if [[ -x "$TARGET/scripts/up.sh" ]]; then (cd "$TARGET" && ./scripts/up.sh); fi
if [[ -x "$TARGET/verify.sh" ]]; then (cd "$TARGET" && ./verify.sh); fi

# commit to repo that holds the service
REPO_ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null || echo '')"
if [[ -z "$REPO_ROOT" ]]; then
  # assume our health_portal repo is parent
  REPO_ROOT="/mnt/nas_storage/repos/health_portal"
fi
cd "$REPO_ROOT"
git add "$TARGET"
git commit -m "${COMMIT_MSG:-install $SERVICE_NAME}" || echo "(i) no changes to commit"
echo "[✓] installed $SERVICE_NAME"
