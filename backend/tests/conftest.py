"""
Pytest configuration and shared fixtures.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.postgres import Base, get_db
from app.core.config import settings

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def compile_jsonb(type_, compiler, **kw):
    return "JSON"

# In-memory SQLite for tests (no external Postgres needed)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    """Fresh DB session per test, rolled back after."""
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db) -> AsyncClient:
    """AsyncClient with DB dependency overridden to use test session."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def job_id() -> str:
    return str(uuid.uuid4())
