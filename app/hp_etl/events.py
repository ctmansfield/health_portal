from typing import Optional, Any
from .db import pg

INSERT_SQL = """
INSERT INTO analytics.data_events (
  person_id, source, kind, code_system, code, display,
  effective_time, effective_start, effective_end,
  value_num, value_text, unit, device_id, status, raw, meta
) VALUES (
  %(person_id)s, %(source)s, %(kind)s, %(code_system)s, %(code)s, %(display)s,
  %(effective_time)s, %(effective_start)s, %(effective_end)s,
  %(value_num)s, %(value_text)s, %(unit)s, %(device_id)s, %(status)s, %(raw)s::jsonb, %(meta)s::jsonb
)
"""


def bulk_insert(rows: list[dict[str, Any]], dsn: Optional[str] = None):
    if not rows:
        return 0
    with pg(dsn) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
    return len(rows)
