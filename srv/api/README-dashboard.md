# Dashboard (srv/api/dashboard)

This document describes the server-rendered dashboard provided under `srv/api`.
It is intentionally lightweight, reads analytics views from the database, and
is intended for local or intranet deployment.

Endpoints
- `GET /login` — enter API key for browser access; stores key in an httpOnly cookie.
- `POST /login` — accepts the API key and sets cookie (redirects to /dashboard).
- `GET /dashboard` — main dashboard page (requires API key if `HP_API_KEY` is set).
- `GET /logout` — clears the API key cookie and redirects to a confirmation page.

Templates
- `srv/api/templates/dashboard.html` — main dashboard page. Shows:
  - Median HR (daily) line chart
  - Daily SpO2 chart (daily min) for the same period
  - Recent AI findings table
- `srv/api/templates/login.html` — login form
- `srv/api/templates/logged_out.html` — logout confirmation

Static
- `srv/api/static/style.css` — styling for the dashboard.

Security
- Browser access is protected by an API key when `HP_API_KEY` is set in the
  environment. The dashboard stores the key in an `hp_api_key` httpOnly cookie
  so interactive use does not require manual header injection.

Runtime
1. Activate the repository virtualenv and set `HP_DSN`:

```bash
. .venv/bin/activate
export HP_DSN="postgresql://health:health_pw@localhost:55432/health"
# optionally set HP_API_KEY to enable auth
export HP_API_KEY="secret"
```

2. Run the app from the repo root so imports resolve correctly:

```bash
uvicorn srv.api.main:app --host 127.0.0.1 --port 8081 --reload
```

3. Open the dashboard in a browser:

- Visit `http://127.0.0.1:8081/login` to provide the API key if required.
- Go to `http://127.0.0.1:8081/dashboard` to view charts.

Notes
- The dashboard reads materialized views (`analytics.mv_daily_vitals`) and
  `analytics.ai_findings`. These views are read-only and will not be modified
  by the dashboard.
- For production deployments, ensure `HP_API_KEY` is set and run behind HTTPS
  so cookies can be marked secure.
