# ADR-0006 — Contracts Registry & Governance

- **Decision**: `core/contracts.yaml` is the single source of truth for DB schema, API, and payload versions (+ compatibility matrix).
- **Status**: Accepted
- **Rationale**: Enables parallel work without collision; explicit bumps for changes.
- **Consequences**: Process requires updating contracts first; CI optional for now (Light Mode).
