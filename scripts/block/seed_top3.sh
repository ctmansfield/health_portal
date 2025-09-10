#!/usr/bin/env bash
set -euo pipefail
# Seeds the top 3 blocks using the Coding Blocks system.
# Usage:
#   scripts/block/seed_top3.sh [--assignees "DB-1:Alice,APP-2:Bob,APP-3:Carol"] [--no-commit]
#
# Notes:
# - Requires scripts/block/open_block.sh from Coding Blocks v0.1.9.
# - If --no-commit is set, skips git commit (still updates registry & files).

ASSIGNEES=""
COMMIT=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --assignees) ASSIGNEES="$2"; shift 2 ;;
    --no-commit) COMMIT=0; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

need=("scripts/block/open_block.sh")
for n in "${need[@]}"; do
  [[ -x "$n" ]] || { echo "[fail] missing $n — install Coding Blocks v0.1.9 first"; exit 2; }
done

# Parse assignees "DB-1:Alice,APP-2:Bob,APP-3:Carol"
get_owner() {
  local id="$1"
  if [[ -n "$ASSIGNEES" ]]; then
    IFS=',' read -r -a pairs <<< "$ASSIGNEES"
    for p in "${pairs[@]}"; do
      key="${p%%:*}" ; val="${p#*:}"
      if [[ "$key" == "$id" ]]; then echo "$val"; return 0; fi
    done
  fi
  echo "${GIT_AUTHOR_NAME:-unknown}"
}

declare -a ids=("DB-1" "APP-2" "APP-3")

for id in "${ids[@]}"; do
  owner="$(get_owner "$id")"
  echo "[seed] opening $id (assignee: $owner)"
  ID="$id" ASSIGNEE="$owner" scripts/block/open_block.sh "$id" "$owner" || { echo "[warn] could not open $id"; }
done

if [[ "$COMMIT" -eq 1 ]] && command -v git >/dev/null 2>&1; then
  git add -A
  git commit -m "chore(block): preseed DB-1, APP-2, APP-3" >/dev/null 2>&1 || true
  echo "[git] preseeding commit created (if there were changes)"
fi

echo "[done] Blocks seeded. Active blocks under blocks/active/"
