#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; ASSIGNEE="${2:-}"
test -n "$ID" && test -n "$ASSIGNEE" || { echo "usage: $0 <ID> <assignee>"; exit 2; }
python - <<PY
import yaml, sys, datetime, os
ID, ASSIGNEE = os.environ.get('ID'), os.environ.get('ASSIGNEE')
with open("blocks/registry.yaml","r",encoding="utf-8") as f:
    data = yaml.safe_load(f)
ok=False
for b in data['blocks']:
    if b['id']==ID:
        b['assignee']=ASSIGNEE
        ok=True
        break
if not ok:
    print("[fail] block not found", ID); sys.exit(2)
with open("blocks/registry.yaml","w",encoding="utf-8") as f:
    yaml.safe_dump(data, f, sort_keys=False)
print("[assign] set assignee", ASSIGNEE, "for", ID)
PY
