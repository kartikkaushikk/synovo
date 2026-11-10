from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# ── FastAPI engine (pooled) ────────────────────────────────────────────────
# Used by API routes.  The pool binds asyncpg connections to the event loop
# that is running when the pool is first used (uvicorn's loop).
engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Celery-worker session factory (NullPool) ───────────────────────────────
@asynccontextmanager
async def worker_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Session factory for use inside Celery tasks (called via asyncio.run()).

    WHY NullPool:
      The module-level ``engine`` above uses asyncpg's connection pool.
      asyncpg binds every pool connection to the event loop that was running
      when the connection was first created.  Each ``asyncio.run()`` call in
      a Celery worker spins up a *new* event loop, so the old pooled
      connections point to a different (now closed) loop →
      ``RuntimeError: Future attached to a different loop``.

      NullPool disables connection reuse: a fresh asyncpg connection is
      created at the start of each ``async with worker_session()`` block and
      closed at the end — always bound to whatever loop is currently running.
    """
    worker_engine = create_async_engine(
        settings.POSTGRES_URL,
        poolclass=NullPool,
        echo=settings.DEBUG,
    )
    factory = async_sessionmaker(
        worker_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    await worker_engine.dispose()
