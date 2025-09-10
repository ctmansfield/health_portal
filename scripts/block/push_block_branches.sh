#!/usr/bin/env bash
set -euo pipefail
OPEN_PR=0; BASE="main"
while [[ $# -gt 0 ]]; do case "$1" in --open-pr) OPEN_PR=1; shift ;; --base) BASE="$2"; shift 2 ;; *) echo "unknown arg: $1"; exit 2;; esac; done
command -v git >/dev/null 2>&1 || { echo "[fail] git not found"; exit 2; }
branches=$(git for-each-ref --format='%(refname:short)' refs/heads/block/ || true)
[ -z "$branches" ] && { echo "[info] no block/* branches"; exit 0; }
for b in $branches; do
  echo "[push] $b"; git push -u origin "$b" || true
  if [[ "$OPEN_PR" -eq 1 ]] && command -v gh >/dev/null 2>&1; then gh pr create -B "$BASE" -H "$b" -t "${b#block/}" -b "Auto PR" || true; fi
done
echo "[done] Push complete."
