#!/usr/bin/env bash
set -euo pipefail
# Run lightweight checks, then guide a manual commit.
# Usage: scripts/hp_manual_commit.sh "your commit message"
MSG="${1:-}"

echo "[preflight] minimal checks"
if [ -f "./VERIFY_ALL.sh" ]; then
  echo "[info] running VERIFY_ALL.sh (if present)"
  bash ./VERIFY_ALL.sh || { echo "[warn] VERIFY_ALL failed; continue? [y/N]"; read -r ans; [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 1; }
else
  echo "[info] no VERIFY_ALL.sh found; skipping"
fi

git add -A
if [ -z "$MSG" ]; then
  echo "[prompt] Enter commit message (end with Ctrl-D):"
  MSG="$(cat)"
fi
git commit -m "$MSG" || { echo "[info] nothing to commit"; exit 0; }

echo "[done] commit created"
