from contextlib import contextmanager
import os
import psycopg

def dsn_from_env(default: str | None = None) -> str:
    return os.getenv("HP_DSN", default or "postgresql://health:health_pw@localhost:55432/health")

@contextmanager
def pg(dsn: str | None = None):
    with psycopg.connect(dsn or dsn_from_env(), autocommit=True) as conn:
        yield conn
