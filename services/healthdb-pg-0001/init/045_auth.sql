-- 045_auth.sql
-- Authentication and RBAC schema for Health Portal

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

CREATE TABLE IF NOT EXISTS analytics.sessions (
  session_id TEXT PRIMARY KEY,
  user_id BIGINT REFERENCES analytics.users(id) ON DELETE CASCADE,
  data JSONB DEFAULT '{}'::jsonb,
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.auth_audit (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  username TEXT,
  action TEXT,
  ip INET,
  user_agent TEXT,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON analytics.sessions(user_id, expires_at);
