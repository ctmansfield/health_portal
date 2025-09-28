#!/usr/bin/env bash
set -euo pipefail
DIR="${1:?Usage: $0 <source_dir> <subject> <out_dir>}"
SUBJECT="${2:-Patient/example}"
OUTDIR="${3:-/tmp/medfiles_to_fhir}"
mkdir -p "$OUTDIR"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDFTXT="$HERE/pdf_to_text.sh"
APPLE="$HERE/parse_apple_pdf_to_fhir.py"
VA_PY="/repos/health_portal/ops/va_bb/parse_va_blue_button.py"
shopt -s nullglob
mapfile -t FILES < <(find "$DIR" -maxdepth 1 -type f \( -iname '*.pdf' -o -iname '*.txt' -o -iname '*.json' -o -iname '*ndjson' \) | sort)
[[ ${#FILES[@]} -gt 0 ]] || { echo "No importable files found in: $DIR" >&2; exit 2; }
for f in "${FILES[@]}"; do
  base="$(basename "$f")"; stem="${base%.*}"; lower="${base,,}"
  case "${f,,}" in
    *.pdf)
      tmp_txt="$OUTDIR/$stem.txt"; "$PDFTXT" "$f" "$tmp_txt"
      if [[ "$lower" =~ va|blue\ button ]]; then
        out="$OUTDIR/${stem}_va.json"; python3 "$VA_PY" "$tmp_txt" "$out" "--subject=$SUBJECT" || echo "[WARN] VA parse failed: $base"
      else
        out="$OUTDIR/${stem}_apple.json"; python3 "$APPLE" --text "$tmp_txt" --out "$out" --subject "$SUBJECT" || echo "[WARN] Apple parse failed: $base"
      fi
      ;;
    *.txt)
      if [[ "$lower" =~ va|blue\ button ]]; then
        out="$OUTDIR/${stem}_va.json"; python3 "$VA_PY" "$f" "$out" "--subject=$SUBJECT" || echo "[WARN] VA parse failed: $base"
      fi
      ;;
    *.json|*ndjson) cp -f "$f" "$OUTDIR/$base" ;;
  esac
done
echo "Converted files in: $OUTDIR"
ls -1 "$OUTDIR" | sed 's/^/  /'
