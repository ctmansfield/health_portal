# Blocks Working Agreement (Lightweight)

- **Open a block** to start work: creates a branch, scaffolds README/PROMPT/CHECKLIST with context.
- **Close a block** to finish: runs optional checks, updates status, commits with a standard message, and (optionally) pushes.
- **No cross-boundary edits.** Paths to touch are listed per block.

## Branch Naming & Commits
- Branch: `block/<ID>-<slug>` (e.g., `block/APP-2-get-report`)
- Commit: `feat(app): complete APP-2` (or `chore(db): complete DB-1`)
- You can open a PR manually or via `gh` CLI if installed.

## Minimal Tooling (no overhead)
- No required CI or protections.
- Scripts are pure bash + optional python (if available).
