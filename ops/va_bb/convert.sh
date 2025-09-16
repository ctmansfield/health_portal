#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: convert.sh <VA_Blue_Button.txt> <out.json> [--subject=Patient/example]" >&2
  exit 2
fi
python3 "$(dirname "$0")/parse_va_blue_button.py" "$1" "$2" "${3:-}"
