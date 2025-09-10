# LLM Coder — VS Code Quickstart

Use VS Code's **Run Task** to pick up and complete Coding Blocks.

## 0) One-time
- Install the Coding Blocks system (v0.1.9+) and this VS Code bundle.
- Ensure the `code` command is available (VS Code → Command Palette → “Shell Command: Install 'code' in PATH”).

## 1) Grab a block
- Press `Ctrl/Cmd + Shift + P` → **Run Task** → `Blocks: List`
- Choose `Blocks: Open (scaffold + open in VS)` and enter the **Block ID** and optional **assignee**.

This creates a branch, scaffolds docs, and opens:
- `blocks/active/<ID>/PROMPT.md` — copy this into your LLM (Continue, Copilot Chat, etc.).
- `blocks/active/<ID>/README.md` — context, allowed paths, acceptance criteria.

## 2) Code with your LLM
- Paste `PROMPT.md` into your LLM tool in VS Code.
- Keep changes within the allowed paths listed in the block README.

## 3) Close the block
- Run Task → `Blocks: Close (commit)` → provide a commit message.
- (Optional) Run Task → `Blocks: Push Branches (and open PRs)` to push and open PRs if you use GitHub CLI.

### Tips
- Need the docs quickly? Many are linked inside `PROMPT.md` and `README.md`.
- Use `Blocks: Seed Top 3` to auto-open DB-1, APP-2, APP-3 for the team.
