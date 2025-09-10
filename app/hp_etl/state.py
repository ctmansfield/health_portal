from .db import pg

def get_state(key: str, dsn: str | None = None) -> str | None:
    with pg(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM analytics.etl_state WHERE key=%s", (key,))
            r = cur.fetchone()
            return r[0] if r else None

def set_state(key: str, value: str, dsn: str | None = None):
    with pg(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO analytics.etl_state(key, value)
                VALUES (%s,%s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
            """, (key, value))
