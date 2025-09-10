# Multi‑Tenant Design (Future‑Ready)

- **Isolation**: per-tenant namespaces or schemas; avoid cross-tenant joins.
- **Config**: feature flags + theme tokens; tenant-scoped API keys.
- **Data**: row-level security (later); explicit tenant_id on report rows.
