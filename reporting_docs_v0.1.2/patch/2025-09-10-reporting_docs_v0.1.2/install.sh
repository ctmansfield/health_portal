#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(pwd)"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${PATCH_DIR}/scaffold"

echo "[install] Installing consolidated reporting design docs..."

mkdir -p "${ROOT_DIR}/docs/reporting_scaffold"
cp -R "${SRC_DIR}/docs/." "${ROOT_DIR}/docs/reporting_scaffold/"

echo "[install] Done."
