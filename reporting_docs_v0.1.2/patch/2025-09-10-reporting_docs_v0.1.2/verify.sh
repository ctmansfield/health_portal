#!/usr/bin/env bash
set -euo pipefail
DOC="docs/reporting_scaffold/Program_System_Design_Consolidated_v0.1.x.md"
test -f "$DOC" || (echo "[fail] Missing $DOC" && exit 2)
sha=$(sha256sum "$DOC" | awk '{print $1}')
echo "[ok] Found $DOC"
echo "[ok] sha256:$sha"
