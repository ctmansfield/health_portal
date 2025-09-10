#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; ASSIGNEE="${2:-}"
if [ -z "$ID" ] || [ -z "$ASSIGNEE" ]; then
  echo "usage: $0 <ID> <assignee>"; exit 2
fi
PYBIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYBIN" ]; then echo "[error] python not found"; exit 2; fi
export ID ASSIGNEE
"$PYBIN" - <<'PY'
import os, sys, yaml
ID=os.environ['ID']; ASSIGNEE=os.environ['ASSIGNEE']
with open("blocks/registry.yaml","r",encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
blocks = data.get('blocks') or []
for b in blocks:
    if b.get('id') == ID:
        b['assignee'] = ASSIGNEE
        break
else:
    print(f"[fail] block {ID} not found"); sys.exit(2)
with open("blocks/registry.yaml","w",encoding="utf-8") as f:
    yaml.safe_dump(data, f, sort_keys=False)
print("[assign] set assignee", ASSIGNEE, "for", ID)
PY
echo "[hint] (optional) open the block: scripts/block/open_block.sh $ID \"$ASSIGNEE\""
