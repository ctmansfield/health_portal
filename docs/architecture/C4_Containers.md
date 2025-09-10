# C4 — Containers (Components at runtime)

```mermaid
flowchart TB
  subgraph Dashboard
    FE[Web Frontend]
- Summary Card
- Full Report View
- Patient Mode
  end
  subgraph App["Application Layer"]
    API[REST API (OpenAPI v1)] --> REND[Renderer]
    API --> FHIR[FHIR/VRS Exporters]
    API --> SIGN[Sign-out & Hashing]
    ING[Ingress Validator] --> API
  end
  FE -->|/reports/*| API
  subgraph Data["Data Tier"]
    DB[(Postgres)]:::core
    VIEWS[(Exec Summary, Analytics)]:::core
  end
  API -->|RW| DB
  DB --> VIEWS
  Pipelines[genomics_stack jobs] -->|report.v1.json| ING

  classDef core fill:#1f77b4,stroke:#0d3b66,color:#fff;
```
**Notes:** Renderer is synchronous in v0.1; export jobs may move async later.
