#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(pwd)"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${PATCH_DIR}/scaffold"

echo "[install] Installing LLM enablement guardrails..."

mkdir -p "${ROOT_DIR}/.github/ISSUE_TEMPLATE"
mkdir -p "${ROOT_DIR}/.github/workflows"
cp -R "${SRC}/.github/." "${ROOT_DIR}/.github/"

cp "${SRC}/CONTRIBUTING.md" "${ROOT_DIR}/CONTRIBUTING.md"
cp "${SRC}/VERIFY_ALL.sh" "${ROOT_DIR}/VERIFY_ALL.sh"
chmod +x "${ROOT_DIR}/VERIFY_ALL.sh"

echo "[install] Done. Open CONTRIBUTING.md for LLM coder guidance."
