"""Database engine and session management."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


# ---------- Async engine (used by FastAPI endpoints) ----------

# We pip-installed psycopg v3 with [binary]. Its async driver is
# 'psycopg', so we swap the dialect in the URL: postgresql+psycopg
async_engine = create_async_engine(
    settings.database_url,
    echo=False,  # set True locally to log every SQL statement
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # detect dead connections after restarts
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, closes it on request end.

    Used as `db: AsyncSession = Depends(get_db)` in endpoint signatures.
    """
    async with AsyncSessionLocal() as session:
        yield session


# ---------- Sync engine (used by Alembic migrations + Celery worker) ----------

# Force psycopg v3 for the sync engine too. SQLAlchemy defaults to
# psycopg2 when no driver is specified, but we install psycopg v3.
sync_database_url = settings.database_url  # already has +psycopg
sync_engine = create_engine(sync_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(sync_engine, autocommit=False, autoflush=False)


# ---------- Base class for all ORM models ----------

class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this.

    DeclarativeBase is the SQLAlchemy 2.0 way — fully typed, supports
    async, much cleaner than the legacy declarative_base().
    """
    pass