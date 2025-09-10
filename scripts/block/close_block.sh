#!/usr/bin/env bash
set -euo pipefail
ID="${1:-}"; MSG="${2:-}"
test -n "$ID" || { echo "usage: $0 <ID> \"commit message\""; exit 2; }

if [ -f "./VERIFY_ALL.sh" ]; then
  echo "[verify] running VERIFY_ALL.sh (if present)"
  bash ./VERIFY_ALL.sh || { echo "[warn] VERIFY_ALL failed; continue? [y/N]"; read -r a; [[ "$a" =~ ^[Yy]$ ]] || exit 1; }
fi

python - <<'PY'
import yaml, os, sys, datetime, shutil
ID=os.environ['ID']
with open("blocks/registry.yaml","r",encoding="utf-8") as f:
    data=yaml.safe_load(f)
ok=False
for b in data['blocks']:
    if b['id']==ID:
        b['status']="done"
        b['closed_at']=datetime.datetime.utcnow().isoformat()+"Z"
        ok=True
        break
if not ok:
    print("[fail] unknown block", ID); sys.exit(2)
with open("blocks/registry.yaml","w",encoding="utf-8") as f:
    yaml.safe_dump(data,f, sort_keys=False)

os.makedirs(f"blocks/done/{ID}", exist_ok=True)
src=f"blocks/active/{ID}"
dst=f"blocks/done/{ID}"
if os.path.isdir(src):
    for fn in os.listdir(src):
        shutil.copy2(os.path.join(src,fn), os.path.join(dst,fn))
    shutil.rmtree(src, ignore_errors=True)
print("[close] moved block to blocks/done/%s" % ID)
PY

if command -v git >/dev/null 2>&1; then
  git add -A
  if [ -z "$MSG" ]; then
    MSG="chore(block): close ${ID}"
  fi
  git commit -m "$MSG" || true
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
  if command -v gh >/dev/null 2>&1; then
    echo "[gh] You can open a PR now: gh pr create -t \"${ID}: ${MSG}\" -b \"Auto-created from close_block.sh\" || true"
  else
    echo "[git] Consider pushing branch ${current_branch} and opening a PR"
  fi
fi
