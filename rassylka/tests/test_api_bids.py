"""
Integration tests for /api/bids endpoints.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models import Bid, DistributionBatch

pytestmark = pytest.mark.asyncio


async def test_list_bids_empty(client):
    resp = await client.get("/api/bids")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


async def test_list_bids_with_data(client, test_engine):
    """Insert a bid, then list."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        bid = Bid(
            source_id=77001,
            name="Тестовая заявка для списка",
            brand="TestBrand",
            model="TM1",
            year="2023",
            spare_part_type="Тест",
            count=1,
            delivery_place="Москва",
            description="",
            buyer_name="Тестер",
            status="new",
            source_url="https://umit.pro/public-bids/77001",
        )
        s.add(bid)
        await s.commit()

    resp = await client.get("/api/bids")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    names = [b["name"] for b in data["items"]]
    assert "Тестовая заявка для списка" in names

    # Clean up
    async with factory() as s:
        from sqlalchemy import delete
        await s.execute(delete(Bid).where(Bid.source_id == 77001))
        await s.commit()


async def test_get_bid_not_found(client):
    resp = await client.get("/api/bids/999999")
    assert resp.status_code == 404


async def test_list_bids_filter_status(client, test_engine):
    """Filter by status."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        bid = Bid(
            source_id=77002,
            name="Заявка фильтр",
            brand="",
            model="",
            year="",
            spare_part_type="",
            count=1,
            delivery_place="",
            description="",
            buyer_name="",
            status="distributing",
            source_url="",
        )
        s.add(bid)
        await s.commit()

    resp = await client.get("/api/bids", params={"status": "distributing"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "distributing"

    # Clean up
    async with factory() as s:
        from sqlalchemy import delete
        await s.execute(delete(Bid).where(Bid.source_id == 77002))
        await s.commit()


async def test_list_bids_search(client, test_engine):
    """Search by name."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        bid = Bid(
            source_id=77003,
            name="УникальноеНазвание12345",
            brand="",
            model="",
            year="",
            spare_part_type="",
            count=1,
            delivery_place="",
            description="",
            buyer_name="",
            status="new",
            source_url="",
        )
        s.add(bid)
        await s.commit()

    resp = await client.get("/api/bids", params={"search": "УникальноеНазвание12345"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    # Clean up
    async with factory() as s:
        from sqlalchemy import delete
        await s.execute(delete(Bid).where(Bid.source_id == 77003))
        await s.commit()
