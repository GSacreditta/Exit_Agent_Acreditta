"""SQLAlchemy session + engine factory.

Two connection modes, auto-detected:

1. **Local / proxy**: read `DATABASE_URL` directly. Works for laptop dev
   (local Postgres) and for Cloud SQL Proxy on the laptop.
2. **Cloud Run**: detect `DB_INSTANCE_CONNECTION_NAME` env var. Use the
   `cloud-sql-python-connector` to open an authenticated socket without
   needing the proxy binary.
"""
from __future__ import annotations
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    cloud_sql_inst = os.getenv("DB_INSTANCE_CONNECTION_NAME")
    if cloud_sql_inst:
        return _cloud_sql_engine(cloud_sql_inst)

    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set (and DB_INSTANCE_CONNECTION_NAME absent — "
            "running locally or via Cloud SQL proxy?)"
        )
    return create_engine(url, pool_pre_ping=True, future=True)


def _cloud_sql_engine(instance: str) -> Engine:
    """Cloud Run path: use the Cloud SQL connector with IAM auth."""
    from google.cloud.sql.connector import Connector, IPTypes

    connector = Connector()
    db_user = os.getenv("DB_USER", "app")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "exit_agent")

    def getconn():
        return connector.connect(
            instance,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type=IPTypes.PUBLIC,
        )

    return create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def _sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def get_session() -> Iterator[Session]:
    """Context manager with auto commit/rollback."""
    s = _sessionmaker()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
