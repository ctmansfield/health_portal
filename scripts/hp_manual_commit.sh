#!/usr/bin/env bash
set -euo pipefail
MSG="${1:-}"
[ -f "./VERIFY_ALL.sh" ] && bash ./VERIFY_ALL.sh || true
git add -A
[ -z "$MSG" ] && MSG="chore: manual commit"
git commit -m "$MSG" || echo "[info] nothing to commit"
