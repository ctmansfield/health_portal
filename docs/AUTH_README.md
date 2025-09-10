AUTH — server-side sessions & RBAC (GEN-008)

This document describes the current auth hardening implemented in the repo and how to verify migrations and seed an initial admin user.

What’s implemented
- Server-side sessions: analytics.sessions stores session_id, user_id, data, expires_at, created_at.
- Session TTL enforcement: get_current_user checks expires_at and deletes expired sessions.
- CSRF: simple double-submit cookie helper (app/hp_etl/csrf.py). Login issues a CSRF cookie; POST /auth/logout requires CSRF token header.
- Session cleanup job: jobs/cleanup_sessions.py and cron entry added to scripts/cron/install_cron.sh
- RBAC: require_role('...') decorator and genomics endpoints now require clinician/admin in prod mode; in dev (no HP_API_KEY set) access is allowed for convenience.

Seeding an admin user
- Use scripts/create_user.py to add a user and assign the admin role.

Example:

  export HP_DSN="postgresql://health:pw@localhost:5432/health"
  # create an admin user (will prompt for password)
  python scripts/create_user.py --username admin --email ops@example.com --role admin

Verify migrations
- Run the verify script to ensure auth tables exist in the DB:

  export HP_DSN="postgresql://..."
  bash scripts/verify_auth_migration.sh

- The script checks for analytics.users, analytics.roles, analytics.user_roles, analytics.sessions, analytics.auth_audit.

Notes
- HP_API_KEY fallback: existing deployments using HP_API_KEY continue to work; HP_API_KEY is treated as a system/admin credential.
- For production, ensure the app runs behind HTTPS and cookies are configured Secure=True. Consider migrating CSRF to a server-side token if attacker model requires it.
