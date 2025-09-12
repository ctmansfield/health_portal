Blocks System — Usage & Playbook (Plain Text)

What is a Block
- A small, parallel unit of work with its own docs:
  - README.md   : scope, contracts, acceptance
  - PROMPT.md   : coder instructions used by Continue
  - CHECKLIST.md: definition of done
  - FINAL_SUMMARY.md: required closeout before moving to done
- Locations:
  - blocks/active/<ID>/
  - blocks/done/<ID>/
  - blocks/backlog/<ID>/

Daily Commands
1) List blocks
   scripts/block/list_blocks.sh

2) Open a block and docs (then use Continue)
   scripts/block/open_block.sh <ID> "Assignee"
   scripts/block/vs_open_block.sh <ID>

3) Work on a branch
   git switch -c <short-slug-for-block>

4) Close a block (after FINAL_SUMMARY.md is filled)
   scripts/block/close_block.sh <ID> "commit message"

PR Flow
- Push branch:
  git push -u origin <branch>
- Create PR:
  gh pr create --title "<title>" --body "See blocks/<state>/<ID>/FINAL_SUMMARY.md" --base main --head <branch>
- Merge:
  gh pr view <num>
  gh pr checks <num> || true
  gh pr merge <num> --squash --delete-branch

PROMPT.md Must Include
- Context and goals
- Guardrails: PHI/PII (no logging), performance, accessibility, versioning
- Run/verify commands
- Reminder to write FINAL_SUMMARY.md

FINAL_SUMMARY.md Must Include
- What changed
- Interfaces (endpoints/views; example requests/responses)
- Tests and how to run them
- Verification steps (local; screenshots ok)
- Risks/follow-ups
- Ops notes (caching, TTLs, metrics)

Troubleshooting
- “No commits between branches”: ensure your feature branch actually has commits:
  git log --oneline main..your-branch
- YAML registry complaints: validate with
  python3 - <<'PY'
import yaml; yaml.safe_load(open('blocks/registry.yaml','r',encoding='utf-8')); print("OK")
PY
- Hooks noisy: re-stage after auto-fixes with:
  git add -A && git add -A
  (fallback) git commit --no-verify -m "msg"
- Ignore junk: add to .gitignore
  **/__pycache__/
  *.pyc
  *.pyo
  *.bak
  *.bak.*
  *.patch
  cron.log

Quick Repair (one block)
- If a block folder is missing docs or has tiny placeholders, run:
  python3 - <<'PY'
from pathlib import Path
BID="UI-7"  # change as needed
base=Path(f'blocks/active/{BID}'); base.mkdir(parents=True, exist_ok=True)
def needs(p): 
    return (not p.exists()) or (len(p.read_text(encoding="utf-8").strip()) < 40) or ("placeholder" in p.read_text(encoding="utf-8").lower())
files={
 base/'README.md': f"{BID} — put scope, contracts, acceptance here.\n",
 base/'PROMPT.md': f"You are implementing {BID}. Goals: code + tests + docs. Fill FINAL_SUMMARY.md before closing.\n",
 base/'CHECKLIST.md': f"# {BID} Checklist\n- [ ] Implement scope\n- [ ] Tests pass\n- [ ] Docs updated\n- [ ] FINAL_SUMMARY.md completed\n",
 base/'FINAL_SUMMARY.md': "# Final Summary\n\nWhat changed:\nInterfaces:\nTests:\nVerification steps:\nRisks & follow-ups:\nOps notes:\n",
}
for p,c in files.items():
    if needs(p): p.write_text(c, encoding="utf-8"); print("[write]", p)
    else: print("[keep ]", p)
PY

End.
