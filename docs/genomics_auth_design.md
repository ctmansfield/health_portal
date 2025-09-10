# GEN-008 — Genomics Authentication & RBAC Design

Status: DRAFT
Owner: ops / platform
Estimate: Medium (design + implementation + migration)

Purpose
-------
This design documents a secure, pragmatic approach to hardening authentication and authorization for genomics features exposed through the Health Portal dashboard and its APIs. It focuses on protecting sensitive genomics data (reports, variants) and enabling role-based access control (RBAC) for clinicians, operations, and researchers.

Goals & Requirements
--------------------
- Strong authentication for endpoints that expose genomics data.
- Role-based authorization: at minimum roles for `clinician`, `ops`, `research` and `admin`.
- Backwards compatibility: existing HP_API_KEY must continue to work as an admin/system key for automation; but user-facing access should move to sessions or tokens.
- Secure browser experience: session cookies with proper security flags, CSRF protection for any state-changing endpoints, and optional SSO/OAuth later.
- Auditability: log auth events and important accesses to sensitive resources.
- Deployable incrementally: support a migration path and feature flags so rollout can be gradual.

Threat Model
------------
Primary threats addressed here:
- Leaked API keys used to access sensitive genomics reports.
- CSRF attacks from browsers causing actions under authenticated sessions.
- Unauthorized or over-privileged users viewing protected patient data.
- Credential theft from insecure storage or transit.

Non-goals (for this iteration)
- Full enterprise SSO (SAML/OIDC) integration — planned as a later phase.
- Fine-grained attribute-based access control (ABAC) — RBAC will suffice for initial rollout.

Options Considered
------------------
1. Keep simple API key only (current):
   - Pros: very simple, works for automation.
   - Cons: not user-friendly, hard to rotate, insufficient for per-user RBAC or browser sessions.

2. JWT bearer tokens (stateless):
   - Pros: scalable, easy for API clients, can encode roles in token.
   - Cons: revocation is harder (need token blacklist), risk of long-lived tokens, complexity for browser flows.

3. Session cookies + server-side sessions (recommended):
   - Pros: straightforward browser UX, server-side revocation, easy to support CSRF tokens, integrates well with RBAC lookups.
   - Cons: requires session store (DB or Redis) and slightly more server state.

4. OAuth2 / OIDC (external provider):
   - Pros: robust SSO, industry standard, supports delegated auth.
   - Cons: requires provider or integration effort; may be overkill for initial rollout.

Recommendation
--------------
Start with server-side sessions (option 3) for user-facing access and retain HP_API_KEY for automation and system-to-system scripts. Plan for future SSO/OIDC integration.

Design Details
--------------

1) Entities & Schema

Create a small user and role model in `analytics` schema. Example SQL (migration file):

```sql services/healthdb-pg-0001/init/045_auth.sql
-- Users and roles for dashboard / genomics access
CREATE TABLE IF NOT EXISTS analytics.users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT,
  full_name TEXT,
  password_hash TEXT NOT NULL,
  disabled BOOLEAN NOT NULL DEFAULT FALSE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.roles (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS analytics.user_roles (
  user_id BIGINT REFERENCES analytics.users(id) ON DELETE CASCADE,
  role_id BIGINT REFERENCES analytics.roles(id) ON DELETE CASCADE,
  PRIMARY KEY(user_id, role_id)
);

-- Server-side sessions
CREATE TABLE IF NOT EXISTS analytics.sessions (
  session_id TEXT PRIMARY KEY,
  user_id BIGINT REFERENCES analytics.users(id) ON DELETE CASCADE,
  data JSONB DEFAULT '{}'::jsonb,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Audit log
CREATE TABLE IF NOT EXISTS analytics.auth_audit (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  username TEXT,
  action TEXT,
  ip INET,
  user_agent TEXT,
  created_at timestamptz NOT NULL DEFAULT now()
);
```

Notes:
- `password_hash` should store a strong hash (bcrypt/argon2). Use a tested library (passlib/argon2) in code, but the schema is library-agnostic.
- Sessions can be stored in this table; a TTL-based cleanup job (cron) should remove expired sessions.

2) Authentication flow

- Login (POST /auth/login):
  - Validate username + password.
  - Create a new session row with session_id = a secure random token (e.g., 32+ bytes base64), set expires_at (e.g., now + 12h).
  - Set cookie `hp_sess` with session_id, attributes: HttpOnly, SameSite=Lax, Secure=True (when HTTPS), Path=/.
  - Record login event in analytics.auth_audit.

- Logout (POST /auth/logout):
  - Remove the session row and delete cookie.

- API Key behavior:
  - HP_API_KEY remains supported: requests with X-API-Key matching HP_API_KEY bypass session checks and are treated as `system` or `admin` role. Log api-key usage into auth_audit.

3) Authorization & RBAC

- Implement a decorator/dependency `require_role(roles: list[str])` that:
  - Reads session from cookie and resolves user_id and roles by joining `analytics.user_roles`.
  - Or accepts X-API-Key for system automation.
  - Raises 403 if user missing role(s).

- Default role mapping:
  - `admin`: full access
  - `clinician`: can view patient reports and findings
  - `ops`: can view VEP status, job logs
  - `research`: can view de-identified aggregate data (later)

4) CSRF protection

- For any state-changing POST/PUT/DELETE endpoints, require CSRF token. Implement double-submit cookie pattern or embed a CSRF token in forms.
- For GET requests (dashboard views) csrf not required.

5) Session security

- Use secure, HttpOnly cookies with SameSite=Lax and Secure flag on HTTPS.
- Session tokens should be single-use for sensitive operations (optional) and rotated on privilege changes.
- Support server-side session invalidation (logout, admin revoke) by deleting session row.

6) Passwords & user management

- Initial admin user can be created via migration or CLI (safe default). Provide a CLI `scripts/create_user.py` that sets password interactively and writes hashed password to DB.
- Password reset flow is out-of-scope for initial rollout (could be added later).

7) Auditing & monitoring

- Log successful/failed logins and HP_API_KEY uses in analytics.auth_audit.
- Surfacing logs to ops via existing monitoring/cron/log file rotation.

8) Migration & Rollout Plan

Phase 0 — prepare (no user impact)
- Add schema migration (services/healthdb-pg-0001/init/045_auth.sql).
- Add a small administrative CLI to create initial user(s) and roles.
- Add code scaffolding: `srv/api/auth_user.py` with login/logout/session management and dependencies.

Phase 1 — opt-in sessions (co-existence)
- Deploy session auth, but keep HP_API_KEY enforcement as fallback.
- Update dashboard login to support username/password and set session cookie.
- Convert genomics endpoints to use `require_role(['clinician'])` where appropriate.

Phase 2 — enforce sessions, deprecate direct API keys
- Announce deprecation of direct HP_API_KEY for user-facing routes.
- Optionally allow API keys for automation only via dedicated secrets management and stricter logging.

Phase 3 — SSO integration (optional)
- Add OIDC/OAuth provider for SSO and map provider groups to internal roles.

9) API / Code Changes (implementation tasks)

- New module: `srv/api/auth_user.py`:
  - `POST /auth/login` — create session
  - `POST /auth/logout` — destroy session
  - `GET /auth/me` — return current user and roles
  - Dependency `get_current_user()` to resolve user from session cookie or HP_API_KEY
  - Dependency `require_role(roles)` for route-level protection

- DB helpers in `app/hp_etl/db.py` used for sessions/roles.

- Update `srv/api/dashboard.py` and `srv/api/v1/genomics.py` to require appropriate roles (e.g., clinician) for protected genomics routes.

10) Tests & Acceptance

- Unit tests for auth flows (login, logout, session lifecycle), RBAC checks, and HP_API_KEY fallback.
- Integration tests using TestClient that simulate login, cookie handling, and role-based access.

11) Operational considerations

- Add cron job to cleanup expired sessions (DELETE FROM analytics.sessions WHERE expires_at < now()).
- Rotate HP_API_KEY periodically and provide procedures for revocation.

12) Backward compatibility

- Keep HP_API_KEY behavior for system automation but scope it to specific endpoints or map it to `admin` role.
- Provide a migration script to seed an initial admin user if needed.

13) Risks & mitigations

- Risk: Storing passwords and sessions incorrectly. Mitigation: use well-tested password hashing libraries and secure cookie flags.
- Risk: Unauthorized access during rollout. Mitigation: phased rollout, feature flags, and detailed auditing.

14) Estimated work breakdown (approx)
- Schema migration + CLI to create user: 1–2 days
- Auth dependency + login/logout routes + tests: 2–3 days
- RBAC enforcement on genomics endpoints + tests: 1–2 days
- CSRF for stateful endpoints and session cleanup job: 1 day
- Documentation + runbooks: 1 day

Total: 1–2 weeks depending on review and environment setup.

Appendix — Example: minimal create-user CLI
```python scripts/create_user.py
# usage: python scripts/create_user.py --username alice
# prompts for password and inserts into analytics.users with hashed password
```

Open questions
--------------
- Do you want to require logins for all dashboard users from day one, or enable a phased approach?
- Is there an existing SSO/OIDC provider we should integrate with later?
