"""Async SQLAlchemy session and engine setup for the application."""

import os

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Base pour les modèles (declare early to avoid circular imports)
Base = declarative_base()

# Engine asynchrone
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

# If running under pytest-xdist, create a per-worker test schema and
# instruct each new connection to use that schema via search_path.
_worker_schema = None
_worker = os.getenv("PYTEST_XDIST_WORKER")
if _worker:  # pragma: no cover - xdist worker initialization
    _worker_schema = settings.TEST_SCHEMA
    # Use a synchronous engine for DDL to ensure CREATE SCHEMA executes cleanly
    sync_engine = sqlalchemy.create_engine(settings.SYNC_DATABASE_URL)
    with sync_engine.connect() as conn:
        conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {_worker_schema}"))
        conn.commit()

    # @event.listens_for(engine.sync_engine, "connect")
    # def _set_search_path(dbapi_connection, connection_record):
    #     # Set the schema on each new connection
    #     cursor = dbapi_connection.cursor()
    #     cursor.execute(f"SET search_path TO {_worker_schema}")
    #     cursor.close()


# Session asynchrone (type-safe factory)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# Dependency FastAPI
async def get_session():
    """FastAPI dependency that yields an AsyncSession bound to the app engine."""
    async with async_session() as session:
        # If a per-worker test schema is configured, ensure the session uses it
        if _worker_schema:  # pragma: no cover - xdist worker context
            await session.execute(text(f"SET search_path TO {_worker_schema}"))
        yield session
