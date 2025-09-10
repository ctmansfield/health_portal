#!/usr/bin/env bash
set -euo pipefail
WF_DIR=".github/workflows"; WF_DISABLED=".github/workflows_disabled"
CO=".github/CODEOWNERS"; CO_BAK=".github/CODEOWNERS.sample"
case "${1:-status}" in
  off) mkdir -p "$WF_DISABLED"; shopt -s nullglob; for f in "$WF_DIR"/*.yml "$WF_DIR"/*.yaml; do mv "$f" "$WF_DISABLED"/; done; shopt -u nullglob; [ -f "$CO" ] && mv "$CO" "$CO_BAK"; echo "automation OFF";;
  on) mkdir -p "$WF_DIR"; shopt -s nullglob; for f in "$WF_DISABLED"/*.yml "$WF_DISABLED"/*.yaml; do mv "$f" "$WF_DIR"/; done; shopt -u nullglob; [ -f "$CO_BAK" ] && mv "$CO_BAK" "$CO"; echo "automation ON";;
  status) [ -d "$WF_DISABLED" ] && [ -z "$(ls -A "$WF_DIR" 2>/dev/null || true)" ] && echo "automation=OFF" || echo "automation=ON";;
  *) echo "usage: $0 {on|off|status}"; exit 2;;
esac
