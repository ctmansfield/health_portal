# ADR-0002 — API Versioning

- **Decision**: Read-only **OpenAPI v1** with version negotiated via `Accept-Version` header; semantic versioning.
- **Status**: Accepted
- **Rationale**: Keeps dashboard decoupled; additive MINOR changes non-breaking.
- **Consequences**: CI must ensure backward compatibility across MINOR; MAJOR requires coordination.
