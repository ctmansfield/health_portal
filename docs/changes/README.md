# Changes Workflow

Goal: Make ongoing changes easy to record during development and tidy to read on release.

Use two tiers:
1) Fragments (per PR): add a small file under changes/unreleased/ named <PR or short id>.<type>.md
   - Types: feature, fix, perf, docs, breaking, security, chore
   - Content: 1–3 lines, user-facing where possible; reference ADRs (e.g., ADR-0006) if relevant.
2) Release aggregation: a script will collect fragments into the root CHANGELOG.md and clear changes/unreleased/.

Examples
- 1234.feature.md
  Added liver labs UI with selectable metrics and CSV export.

- 1235.fix.md
  Fixed dashboard /events 404; added missing script include; updated tests.

Skipping
- Add label skip-changelog or commit message [skip-changelog] for non-user-facing chores.
