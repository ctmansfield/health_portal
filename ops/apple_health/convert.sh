#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: convert.sh <export.xml> <out.json> [--subject Patient/example]" >&2
  exit 2
fi
python3 "$(dirname "$0")/parse_health.py" "$1" "$2" "${3:-}"
