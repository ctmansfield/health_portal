#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(pwd)"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${PATCH_DIR}/scaffold"

echo "[install] Installing parallel feature plan & interface contracts..."

mkdir -p "${ROOT_DIR}/docs/reporting_scaffold"
cp -R "${SRC_DIR}/docs/." "${ROOT_DIR}/docs/reporting_scaffold/"

mkdir -p "${ROOT_DIR}/core"
cp -R "${SRC_DIR}/core/." "${ROOT_DIR}/core/"

mkdir -p "${ROOT_DIR}/api"
cp -R "${SRC_DIR}/api/." "${ROOT_DIR}/api/"

mkdir -p "${ROOT_DIR}/schemas"
cp -R "${SRC_DIR}/schemas/." "${ROOT_DIR}/schemas/"

echo "[install] Done. See docs/reporting_scaffold/Parallel_Workstreams_and_Interface_Contracts.md"
