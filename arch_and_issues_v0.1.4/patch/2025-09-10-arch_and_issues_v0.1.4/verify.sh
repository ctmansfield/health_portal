#!/usr/bin/env bash
set -euo pipefail
for f in \
  "docs/reporting_scaffold/System_Architecture_and_Design.md" \
  "docs/reporting_scaffold/Platform_System_Improvements.md" \
  "docs/reporting_scaffold/diagrams/architecture.mmd" \
  "issues/parallel_plan.issues.yaml" \
  "scripts/create_issues.sh" \
; do
  test -f "$f" || (echo "[fail] Missing $f" && exit 2)
  echo "[ok] Found $f"
done
echo "[verify] Bundle looks good."
