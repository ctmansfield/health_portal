#!/usr/bin/env bash
set -euo pipefail
PATCH_DIR="${1:-}"; [[ -n "$PATCH_DIR" && -d "$PATCH_DIR" ]] || { echo "usage: $0 /path/to/patch_dir"; exit 1; }

yaml_get(){ grep -E "^[[:space:]]*$1:" "$2" | head -n1 | sed -E "s/^[[:space:]]*$1:[[:space:]]*//"; }

PATCH_FILE="$PATCH_DIR/PATCH.yaml"; [[ -f "$PATCH_FILE" ]] || { echo "PATCH.yaml missing"; exit 1; }

TARGET="$(yaml_get target "$PATCH_FILE")"
SERVICE_NAME="$(yaml_get service_name "$PATCH_FILE")"
COMMIT_MSG="$(yaml_get commit_message "$PATCH_FILE")"
ROOT_MODE="$(yaml_get root_mode "$PATCH_FILE" || true)"

[[ -n "$SERVICE_NAME" ]] || { echo "bad PATCH.yaml (missing service_name)"; exit 1; }

# Default repo root where we commit changes
REPO_ROOT="/mnt/nas_storage/repos/health_portal"
[[ -d "$REPO_ROOT/.git" ]] || { echo "repo not initialized at $REPO_ROOT"; exit 1; }

echo "[+] applying $SERVICE_NAME"

if [[ "${ROOT_MODE:-false}" == "true" ]]; then
  # Root-wide add/update: copy into repo root (no --delete!)
  rsync -a --exclude 'PATCH.yaml' --exclude '.DS_Store' "$PATCH_DIR/" "$REPO_ROOT/"
  # Optional patch-local verify
  if [[ -x "$PATCH_DIR/verify.sh" ]]; then (cd "$REPO_ROOT" && bash "$PATCH_DIR/verify.sh"); fi
  cd "$REPO_ROOT"
  git add -A
  git commit -m "${COMMIT_MSG:-install $SERVICE_NAME}" || echo "(i) no changes to commit"
  echo "[✓] installed (root mode) $SERVICE_NAME"
  exit 0
fi

# Legacy target mode (single directory)
[[ -n "$TARGET" ]] || { echo "bad PATCH.yaml (need target or set root_mode: true)"; exit 1; }
mkdir -p "$TARGET"
rsync -a --delete --exclude 'PATCH.yaml' --exclude '.DS_Store' "$PATCH_DIR/" "$TARGET/"

# start + verify if scripts exist in target
if [[ -x "$TARGET/scripts/up.sh" ]]; then (cd "$TARGET" && ./scripts/up.sh); fi
if [[ -x "$TARGET/verify.sh" ]]; then (cd "$TARGET" && ./verify.sh); fi

cd "$REPO_ROOT"
git add "$TARGET"
git commit -m "${COMMIT_MSG:-install $SERVICE_NAME}" || echo "(i) no changes to commit"
echo "[✓] installed (target mode) $SERVICE_NAME"
