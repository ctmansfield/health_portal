#!/usr/bin/env bash
set -euo pipefail
ASSIGNEES=""; while [[ $# -gt 0 ]]; do case "$1" in --assignees) ASSIGNEES="$2"; shift 2;; *) echo "unknown arg: $1"; exit 2;; esac; done
get_owner(){ local id="$1"; if [[ -n "$ASSIGNEES" ]]; then IFS=',' read -r -a pairs <<< "$ASSIGNEES"; for p in "${pairs[@]}"; do key="${p%%:*}"; val="${p#*:}"; [[ "$key" == "$id" ]] && { echo "$val"; return 0; }; done; fi; echo "${GIT_AUTHOR_NAME:-unknown}"; }
for id in DB-1 APP-2 APP-3; do owner="$(get_owner "$id")"; ID="$id" ASSIGNEE="$owner" scripts/block/open_block.sh "$id" "$owner" || true; done
if command -v git >/dev/null 2>&1; then git add -A; git commit -m "chore(block): preseed DB-1, APP-2, APP-3" >/dev/null 2>&1 || true; fi
