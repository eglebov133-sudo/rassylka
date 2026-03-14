"""
Shared test fixtures for BidRoute AI.

Provides:
- In-memory async SQLite database
- AsyncSession with per-test isolation
- httpx.AsyncClient wired to the FastAPI app
"""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.database import Base, get_db
from backend.models import (
    Bid, Supplier, DistributionBatch, DistributionLog,
    RoutingRule, SmtpAccount, Campaign, CampaignRecipient,
    MonitorTest, MonitorRun, MonitorResult,
)


# ── Engine & session factory (in-memory) ──

TEST_DATABASE_URL = "sqlite+aiosqlite://"

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Yield a transactional session that rolls back after every test."""
    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine):
    """
    httpx.AsyncClient connected to the FastAPI app,
    with get_db overridden to use the test database.

    Also patches backend.database.async_session and
    backend.routers.tracking.async_session so routers that
    use async_session directly (tracking, unsubscribe) also
    hit the in-memory test DB.
    """
    import httpx
    import backend.database
    import backend.routers.tracking
    from backend.main import app

    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Patch module-level async_session used by tracking router
    original_db_session = backend.database.async_session
    original_tracking_session = backend.routers.tracking.async_session
    backend.database.async_session = async_session_factory
    backend.routers.tracking.async_session = async_session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    # Restore originals
    backend.database.async_session = original_db_session
    backend.routers.tracking.async_session = original_tracking_session
    app.dependency_overrides.clear()


# ── Helpers for creating test data ──

@pytest_asyncio.fixture
async def sample_bid(db_session: AsyncSession):
    """Create and return a sample Bid."""
    bid = Bid(
        source_id=99999,
        name="Гидромотор 310.3.112 для экскаватора",
        brand="Caterpillar",
        model="320D",
        year="2018",
        spare_part_type="Гидромоторы",
        count=2,
        delivery_place="Москва",
        description="Требуется гидромотор 310.3.112",
        buyer_name="ООО Стройтех",
        status="new",
        source_url="https://umit.pro/public-bids/99999",
    )
    db_session.add(bid)
    await db_session.flush()
    return bid


@pytest_asyncio.fixture
async def sample_supplier(db_session: AsyncSession):
    """Create and return a sample Supplier."""
    supplier = Supplier(
        company_name="ООО ГидроСнаб",
        email="hydro@test.ru",
        phone="+79001234567",
        contact_person="Иван Петров",
        categories=["Гидромоторы", "Гидравлика"],
        regions=["Москва", "МО"],
        description="Поставщик гидравлических моторов Caterpillar",
        source="manual",
        website="https://hydrosnab.test",
        active=True,
    )
    db_session.add(supplier)
    await db_session.flush()
    return supplier
