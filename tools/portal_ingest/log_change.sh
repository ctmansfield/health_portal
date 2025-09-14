
#!/usr/bin/env bash
# Append a structured changelog entry.
# Usage: tools/portal_ingest/log_change.sh "<what changed>" "<why / context>" [category]
set -euo pipefail
WHAT="${1:-}"
WHY="${2:-}"
CATEGORY="${3:-ops}"
if [[ -z "${WHAT}" || -z "${WHY}" ]]; then
  echo "Usage: $0 \"<what changed>\" \"<why / context>\" [category]" >&2
  exit 2
fi
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
LOG="${REPO_ROOT}/docs/CHANGELOG_portal_ingest.md"
TS="$(date -Is)"
USER_NAME="${SUDO_USER:-${USER:-unknown}}"
HOST="$(hostname)"
{
  echo
  echo "### ${TS} — ${CATEGORY} — ${USER_NAME}@${HOST}"
  echo "- **What:** ${WHAT}"
  echo "- **Why:** ${WHY}"
} >> "${LOG}"
echo "[log] appended to ${LOG}"
