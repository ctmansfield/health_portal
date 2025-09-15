# Health Portal — Documentation

Welcome. This docs site uses a simple structure:

- tutorials/ — optional guided onboarding
- how-to/ — task-focused steps (do X)
- reference/ — APIs, schemas, contracts, glossary (facts)
- explanations/ — architecture, tradeoffs, design briefs (why)
- runbooks/ — operations (backup/restore, incidents, releases)
- changes/ — ongoing change fragments and weekly status (see README inside)

Start here:
- Architecture & ADRs: explanations/architecture/
- API Reference: reference/api/
- How-to: how-to/
- Runbooks: runbooks/
- Changes (Unreleased): changes/unreleased/
- Released notes: ../../CHANGELOG.md

Conventions
- Prefer small PRs with a change fragment under changes/unreleased/.
- For decisions, add an ADR under explanations/architecture/ADRs and reference it from the change fragment.
- Keep how-to (do) and explanations (why) separate for clarity.
