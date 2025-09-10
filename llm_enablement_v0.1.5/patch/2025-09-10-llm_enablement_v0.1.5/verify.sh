#!/usr/bin/env bash
set -euo pipefail
test -f ".github/PULL_REQUEST_TEMPLATE.md" || (echo "[fail] missing PR template" && exit 2)
test -f ".github/CODEOWNERS" || (echo "[fail] missing CODEOWNERS" && exit 2)
test -f ".github/workflows/verify_all.yml" || (echo "[fail] missing workflow" && exit 2)
test -f "CONTRIBUTING.md" || (echo "[fail] missing CONTRIBUTING.md" && exit 2)
echo "[verify] LLM enablement files present."
