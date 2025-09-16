# Multi-backend management (profiles)

See `config/backends.json` for editable profiles. Do not add secrets here.

Guardrails:
- Generated files are git-ignored.
- A grep guard (optional) should prevent hard-coded URLs in `src/` (not included by default).
- Profiles are descriptive only; actual auth credentials live in your secret manager.
