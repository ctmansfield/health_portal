#!/usr/bin/env bash
set -euo pipefail
DEST_REPO="${1:-/repos/health_portal}"
read -r -p "Remove files added by patch? (y/N) " ans
[[ "${ans,,}" == "y" ]] || { echo "Aborted."; exit 0; }

rm -rf "$DEST_REPO/docs/project/PROJECT_BOARD.md" \
       "$DEST_REPO/.github/ISSUE_TEMPLATE/bug_report.md" \
       "$DEST_REPO/.github/ISSUE_TEMPLATE/feature_request.md" \
       "$DEST_REPO/tools/project_board" \
       "$DEST_REPO/.project/issues" \
       "$DEST_REPO/CHANGELOG-PATCH.md"

pushd "$DEST_REPO" >/dev/null
git add -A
git commit -m "Remove project board scaffolding (patch uninstall)"
popd >/dev/null

echo "Uninstall complete."
