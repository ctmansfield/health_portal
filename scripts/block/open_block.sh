#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; ASSIGNEE="${2:-${GIT_AUTHOR_NAME:-unknown}}"
test -n "$ID" || { echo "usage: $0 <ID> [assignee]"; exit 2; }
BRANCH="block/${ID}-$(echo "$ID" | tr '[:upper:]' '[:lower:]')"

# Read registry via python and render templates
python - <<'PY' || { echo "[error] python is required for open_block.sh"; exit 2; }
import yaml, os, sys, datetime, re
from jinja2 import Template

ID=os.environ['ID']; ASSIGNEE=os.environ['ASSIGNEE']

with open("blocks/registry.yaml","r",encoding="utf-8") as f:
    data=yaml.safe_load(f)
blk=None
for b in data['blocks']:
    if b['id']==ID:
        blk=b; break
if not blk:
    print("[fail] unknown block", ID); sys.exit(2)

blk.setdefault('assignee', ASSIGNEE)
blk['status']="active"
opened_at=datetime.datetime.utcnow().isoformat()+"Z"

# render files
os.makedirs(f"blocks/active/{ID}", exist_ok=True)
def render(src, dst, context):
    with open(src,"r",encoding="utf-8") as f: tmpl=Template(f.read())
    with open(dst,"w",encoding="utf-8") as out: out.write(tmpl.render(**context))

ctx=dict(id=blk['id'], title=blk['title'], component=blk['component'], status=blk['status'], assignee=blk['assignee'], opened_at=opened_at,
         docs=blk.get('context',{}).get('docs',[]), touches=blk.get('context',{}).get('touches',[]), acceptance=blk.get('context',{}).get('acceptance',[]))

render("blocks/templates/BLOCK_README.md.tmpl", f"blocks/active/{ID}/README.md", ctx)
render("blocks/templates/PROMPT.md.tmpl", f"blocks/active/{ID}/PROMPT.md", ctx)
render("blocks/templates/CHECKLIST.md.tmpl", f"blocks/active/{ID}/CHECKLIST.md", ctx)

# write back registry
for i,b in enumerate(data['blocks']):
    if b['id']==ID:
        data['blocks'][i]['status']="active"
        data['blocks'][i]['assignee']=blk['assignee']
        data['blocks'][i]['opened_at']=opened_at
        break
with open("blocks/registry.yaml","w",encoding="utf-8") as f:
    yaml.safe_dump(data,f, sort_keys=False)
print("[open] rendered block at blocks/active/%s" % ID)
PY

# create branch (non-fatal if git not available)
if command -v git >/dev/null 2>&1; then
  git checkout -b "$BRANCH" >/dev/null 2>&1 || echo "[info] could not create branch (maybe exists)"
  git add "blocks/active/${ID}" "blocks/registry.yaml"
  git commit -m "chore(block): open ${ID}" >/dev/null 2>&1 || true
  echo "[git] branch ready: $BRANCH"
fi

echo "[hint] Use PROMPT.md for LLM coders and README.md for context"
