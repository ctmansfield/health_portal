#!/usr/bin/env bash
set -euo pipefail
in="$1"; out="$2"
if command -v pdftotext >/dev/null 2>&1; then
  pdftotext -layout -nopgbrk "$in" "$out"
else
  python3 - <<PY "$in" "$out"
import sys
from pdfminer.high_level import extract_text
text = extract_text(sys.argv[1])
open(sys.argv[2],'w',encoding='utf-8').write(text)
PY
fi
