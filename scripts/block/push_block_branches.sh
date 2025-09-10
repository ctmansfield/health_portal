#!/usr/bin/env bash
set -euo pipefail
# Pushes all local 'block/*' branches to origin (creates upstream) and optionally opens PRs.
# Usage:
#   scripts/block/push_block_branches.sh [--open-pr] [--base main]
#
OPEN_PR=0
BASE="main"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --open-pr) OPEN_PR=1; shift ;;
    --base) BASE="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

command -v git >/dev/null 2>&1 || { echo "[fail] git not found"; exit 2; }
branches=$(git for-each-ref --format='%(refname:short)' refs/heads/block/ || true)
if [[ -z "$branches" ]]; then
  echo "[info] no block/* branches found"
  exit 0
fi

for b in $branches; do
  echo "[push] $b"
  git push -u origin "$b" || true
  if [[ "$OPEN_PR" -eq 1 ]] && command -v gh >/dev/null 2>&1; then
    title="${b#block/}"
    gh pr create -B "$BASE" -H "$b" -t "$title" -b "Auto PR for $b" || true
  fi
done
echo "[done] Push complete."
