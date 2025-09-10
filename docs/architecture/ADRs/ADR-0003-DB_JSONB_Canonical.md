# ADR-0003 — DB Strategy: JSONB Canonical + Normalized

- **Decision**: Store canonical report payloads in JSONB, with normalized tables for queryability.
- **Status**: Accepted
- **Rationale**: Preserve full fidelity; enable indexes and views without losing raw structure.
- **Consequences**: Write path validates JSON against schema; views expose stable shapes.
