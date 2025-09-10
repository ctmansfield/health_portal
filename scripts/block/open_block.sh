#!/usr/bin/env bash
set -euo pipefail
# NO-EXTERNAL-DEPS: open block by id; render files; set status=active
ID="${1:-}"; ASSIGNEE="${2:-${GIT_AUTHOR_NAME:-unknown}}"
test -n "$ID" || { echo "usage: $0 <ID> [assignee]"; exit 2; }
PYBIN="$(command -v python3 || command -v python || true)"
if [ -z "$PYBIN" ]; then echo "[error] python not found"; exit 2; fi
export ID ASSIGNEE
$PYBIN - <<'PY'
import os, re, sys, datetime, pathlib
ID=os.environ["ID"]; ASSIGNEE=os.environ.get("ASSIGNEE","unknown")
reg=pathlib.Path("blocks/registry.yaml")
reg.parent.mkdir(parents=True, exist_ok=True)
if not reg.exists():
    reg.write_text("blocks: []\n", encoding="utf-8")
text=reg.read_text(encoding="utf-8")
m=re.search(r"(?ms)^[ \t]*-[ \t]+id:[ \t]*"+re.escape(ID)+r"[^\n]*\n(.*?)(?=^[ \t]*-[ \t]+id:|\Z)",text)
if not m:
    print(f"[warn] {ID} not in registry; adding minimal entry")
    text += f"- id: {ID}\n  title: {ID}\n  component: app\n  status: active\n  deps: []\n  context: {{docs: [], touches: [], acceptance: []}}\n"
    reg.write_text(text, encoding="utf-8")
    text=reg.read_text(encoding="utf-8")
    m=re.search(r"(?ms)^[ \t]*-[ \t]+id:[ \t]*"+re.escape(ID)+r"[^\n]*\n(.*?)(?=^[ \t]*-[ \t]+id:|\Z)",text)
seg=m.group(0)
def get_list(label):
    out=[]; lines=seg.splitlines(); idx=None
    for i,l in enumerate(lines):
        if re.match(rf"^[ \t]*{label}:\s*$", l): idx=i; break
    if idx is None: return out
    for j in range(idx+1,len(lines)):
        l=lines[j]
        if re.match(r"^[ \t]*-\s+", l): out.append(re.sub(r"^[ \t]*-\s+","",l).strip())
        elif re.match(r"^[ \t]*[A-Za-z_]+\s*:", l): break
    return out
def get_scalar(label, default=""):
    r=re.search(rf"^[ \t]*{label}:[ \t]*(.+)$", seg, re.M)
    return r.group(1).strip() if r else default
title=get_scalar("title",ID); component=get_scalar("component","app")
docs=get_list("docs"); touches=get_list("touches"); acceptance=get_list("acceptance")
opened_at=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
blk=pathlib.Path(f"blocks/active/{ID}"); blk.mkdir(parents=True, exist_ok=True)
(blk/"README.md").write_text(f"# {ID} — {title}\n\n**Component:** {component}  \n**Status:** active  \n**Assignee:** {ASSIGNEE}  \n**Opened:** {opened_at}\n\n## Context & Links\n"+ "".join([f"- {d}\n" for d in docs]) +"\n## Paths You May Touch\n"+ "".join([f"- {p}\n" for p in touches]) +"\n## Acceptance Criteria\n"+ "".join([f"- [ ] {a}\n" for a in acceptance]) + "\n", encoding="utf-8")
(blk/"PROMPT.md").write_text(f"# PROMPT for LLM Coder — {ID} ({title})\n\nBoundaries: {component}; use only listed paths.\n", encoding="utf-8")
(blk/"CHECKLIST.md").write_text("# Checklist\n" + "".join([f"- [ ] {a}\n" for a in acceptance]), encoding="utf-8")
# update status & assignee
seg_new=re.sub(r"(^[ \t]*status:[ \t]*).*$", r"\1active", seg, count=1, flags=re.M)
if re.search(r"^[ \t]*assignee:", seg_new, re.M):
    seg_new=re.sub(r"(^[ \t]*assignee:[ \t]*).*$", rf"\1{ASSIGNEE}", seg_new, count=1, flags=re.M)
else:
    seg_new=re.sub(r"(^[ \t]*title:.*$)", rf"\1\n    assignee: {ASSIGNEE}", seg_new, count=1, flags=re.M)
start,end=m.span(); reg.write_text(text[:start]+seg_new+text[end:], encoding="utf-8")
print(f"[open] blocks/active/{ID}")
PY
BRANCH="block/${ID}-$(echo "$ID" | tr '[:upper:]' '[:lower:]')"
if command -v git >/dev/null 2>&1; then
  git checkout -b "$BRANCH" >/dev/null 2>&1 || true
  git add "blocks/active/${ID}" "blocks/registry.yaml" || true
  git commit -m "chore(block): open ${ID}" >/dev/null 2>&1 || true
fi
