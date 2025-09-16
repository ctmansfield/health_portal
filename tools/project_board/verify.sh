#!/usr/bin/env bash
set -euo pipefail
DEST_REPO="${1:-/repos/health_portal}"
for f in \
  "$DEST_REPO/docs/project/PROJECT_BOARD.md" \
  "$DEST_REPO/.github/ISSUE_TEMPLATE/bug_report.md" \
  "$DEST_REPO/.github/ISSUE_TEMPLATE/feature_request.md" \
  "$DEST_REPO/tools/project_board/bootstrap_issues.sh" \
  "$DEST_REPO/.project/issues/01-epic-00-repo-plumbing-&-env.md"
do
  [[ -f "$f" ]] && echo "OK  - $f" || { echo "MISS- $f"; exit 1; }
done
echo "Verification passed."
