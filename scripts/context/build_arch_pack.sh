#!/usr/bin/env bash
set -euo pipefail
GENOMICS_PATH="${1:-}"
ROOT="$(pwd)"; OUT_DIR="${ROOT}/context/arch"; OUT_FILE="${OUT_DIR}/LLM_SERVER_ARCH.md"
mkdir -p "$OUT_DIR"
{
  echo "# LLM Server & Systems Architecture — Context Pack"
  echo "_Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")_"
} > "$OUT_FILE"
for f in docs/architecture/**/*.md docs/**/System_Architecture*.md docs/**/LLM_Server*.md docs/**/ADR*.md; do
  [ -f "$f" ] || continue
  echo -e "\n---\n\n### $f\n" >> "$OUT_FILE"
  echo '```md' >> "$OUT_FILE"; sed -e 's/\t/    /g' "$f" >> "$OUT_FILE"; echo -e '\n```' >> "$OUT_FILE"
done
echo "[done] wrote $OUT_FILE"
