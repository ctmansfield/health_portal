#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(pwd)"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${PATCH_DIR}/scaffold"

mkdir -p "${ROOT_DIR}/docs/reporting_scaffold/diagrams"
cp -R "${SRC_DIR}/docs/." "${ROOT_DIR}/docs/reporting_scaffold/"
mkdir -p "${ROOT_DIR}/issues"
cp -R "${SRC_DIR}/issues/." "${ROOT_DIR}/issues/"
mkdir -p "${ROOT_DIR}/scripts"
cp -R "${SRC_DIR}/scripts/." "${ROOT_DIR}/scripts/"
echo "[install] Installed docs and issues bundle."
