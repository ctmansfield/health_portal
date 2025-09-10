#!/usr/bin/env bash
set -euo pipefail
# Toggle repo automation without deleting anything.
# Usage: scripts/hp_light_mode.sh {on|off|status}
WF_DIR=".github/workflows"
WF_DISABLED=".github/workflows_disabled"
CODEOWNERS=".github/CODEOWNERS"
CODEOWNERS_BAK=".github/CODEOWNERS.sample"

cmd="${1:-status}"

status() {
  if [ -d "$WF_DISABLED" ] && [ -z "$(ls -A "$WF_DIR" 2>/dev/null || true)" ]; then
    echo "automation=OFF"
  else
    echo "automation=ON"
  fi
  if [ -f "$CODEOWNERS_BAK" ] && [ ! -f "$CODEOWNERS" ]; then
    echo "codeowners=OFF"
  else
    echo "codeowners=ON"
  fi
}

off() {
  mkdir -p "$WF_DISABLED"
  if [ -d "$WF_DIR" ]; then
    # move only .yml/.yaml to disabled folder
    shopt -s nullglob
    for f in "$WF_DIR"/*.yml "$WF_DIR"/*.yaml; do
      mv "$f" "$WF_DISABLED"/
    done
    shopt -u nullglob
  fi
  if [ -f "$CODEOWNERS" ]; then
    mv "$CODEOWNERS" "$CODEOWNERS_BAK"
  fi
  echo "[light-mode] automation OFF (workflows moved; CODEOWNERS disabled)"
  status
}

on() {
  if [ -d "$WF_DISABLED" ]; then
    shopt -s nullglob
    mkdir -p "$WF_DIR"
    for f in "$WF_DISABLED"/*.yml "$WF_DISABLED"/*.yaml; do
      mv "$f" "$WF_DIR"/
    done
    shopt -u nullglob
  fi
  if [ -f "$CODEOWNERS_BAK" ]; then
    mv "$CODEOWNERS_BAK" "$CODEOWNERS"
  fi
  echo "[light-mode] automation ON (workflows restored; CODEOWNERS restored)"
  status
}

case "$cmd" in
  on) on ;;
  off) off ;;
  status) status ;;
  *) echo "usage: $0 {on|off|status}" ; exit 2 ;;
esac
