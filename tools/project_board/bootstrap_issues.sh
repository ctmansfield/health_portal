#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${1:-/repos/health_portal}"
REPO_SLUG="${2:-}"

command -v gh >/dev/null || { echo "Install gh CLI first (https://cli.github.com/)"; exit 1; }

pushd "$REPO_DIR" >/dev/null
if [[ -z "$REPO_SLUG" ]]; then
  ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
  if [[ "$ORIGIN_URL" =~ github.com[:/](.+/[^/.]+)(\.git)?$ ]]; then
    REPO_SLUG="${BASH_REMATCH[1]}"
  else
    echo "Pass REPO_SLUG, e.g. ctmansfield/health_portal"; exit 1
  fi
fi

for L in epic cds fhir ingest terminology views ui genomics ehr cerner security rpm compliance good-first-issue p1 p2 p3; do
  gh label create "$L" --color BFD4F2 --description "$L" || true
done

for M in "M0 Foundations" "M1 Ingest" "M2 CDS" "M3 UI" "M4 Genomics" "M5 Pilot"; do
  gh api -X POST "repos/$REPO_SLUG/milestones" -f title="$M" >/dev/null 2>&1 || true
done

shopt -s nullglob
for FILE in .project/issues/*.md; do
  TITLE="$(sed -n 's/^title:\s*//p' "$FILE" | head -1 | tr -d '\"' )"
  LABELS="$(sed -n 's/^labels:\s*//p' "$FILE" | head -1)"
  MILE="$(sed -n 's/^milestone:\s*//p' "$FILE" | head -1 | tr -d '\"')"
  BODY="$(awk 'f;/^---$/{f=1}' "$FILE")"

  CMD=(gh issue create --repo "$REPO_SLUG" --title "$TITLE" --body "$BODY")
  if [[ -n "$LABELS" ]]; then
    LABS=$(python3 - <<'PY'
import sys, json
print(" ".join(["-l "+x for x in json.loads(sys.stdin.read())]))
PY
<<< "$LABELS")
    CMD+=($LABS)
  fi
  if [[ -n "$MILE" ]]; then
    CMD+=(--milestone "$MILE")
  fi
  echo "gh: ${CMD[*]}"
  "${CMD[@]}"
done

popd >/dev/null
echo "Issues created."
