"""
Integration tests for /api/track and /api/unsubscribe endpoints.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import delete

from backend.models import (
    Bid, Supplier, DistributionBatch, DistributionLog,
)

pytestmark = pytest.mark.asyncio


async def _setup_tracking_data(test_engine):
    """Create a full chain: Bid -> Batch -> Log with a click_token."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        bid = Bid(
            source_id=88001,
            name="Трекинг-тест заявка",
            brand="",
            model="",
            year="",
            spare_part_type="",
            count=1,
            delivery_place="",
            description="",
            buyer_name="",
            status="distributing",
            source_url="https://umit.pro/public-bids/88001",
        )
        s.add(bid)
        await s.flush()

        supplier = Supplier(
            company_name="ООО Трекинг-Тест",
            email="tracking@test.ru",
            active=True,
            unsubscribe_token="unsub-test-token-123",
        )
        s.add(supplier)
        await s.flush()

        batch = DistributionBatch(
            bid_id=bid.id,
            batch_number=1,
            status="sent",
        )
        s.add(batch)
        await s.flush()

        log = DistributionLog(
            batch_id=batch.id,
            supplier_id=supplier.id,
            email_status="sent",
            click_token="test-click-token-abc",
        )
        s.add(log)
        await s.commit()

        return {
            "bid_id": bid.id,
            "supplier_id": supplier.id,
            "batch_id": batch.id,
            "log_id": log.id,
        }


async def _cleanup_tracking_data(test_engine, ids):
    """Remove all test tracking data."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        await s.execute(delete(DistributionLog).where(DistributionLog.id == ids["log_id"]))
        await s.execute(delete(DistributionBatch).where(DistributionBatch.id == ids["batch_id"]))
        await s.execute(delete(Supplier).where(Supplier.id == ids["supplier_id"]))
        await s.execute(delete(Bid).where(Bid.id == ids["bid_id"]))
        await s.commit()


async def test_track_open_valid_token(client, test_engine):
    """Opening a valid token should return a 1x1 GIF pixel."""
    ids = await _setup_tracking_data(test_engine)
    try:
        resp = await client.get("/api/track/open/test-click-token-abc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/gif"
        assert len(resp.content) > 0  # has pixel data
    finally:
        await _cleanup_tracking_data(test_engine, ids)


async def test_track_open_invalid_token(client):
    """Invalid token should still return pixel (200)."""
    resp = await client.get("/api/track/open/nonexistent-token")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/gif"


async def test_track_click_valid_token(client, test_engine):
    """Valid token click should redirect to bid URL."""
    ids = await _setup_tracking_data(test_engine)
    try:
        resp = await client.get(
            "/api/track/test-click-token-abc",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "umit.pro" in resp.headers.get("location", "")
    finally:
        await _cleanup_tracking_data(test_engine, ids)


async def test_track_click_invalid_token(client):
    """Invalid token should redirect to umit.pro fallback."""
    resp = await client.get(
        "/api/track/nonexistent-token",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "umit.pro" in resp.headers.get("location", "")


async def test_unsubscribe_valid_token(client, test_engine):
    """Valid unsubscribe token should deactivate supplier."""
    ids = await _setup_tracking_data(test_engine)
    try:
        resp = await client.get("/api/unsubscribe/unsub-test-token-123")
        assert resp.status_code == 200
        assert "отписались" in resp.text
    finally:
        await _cleanup_tracking_data(test_engine, ids)


async def test_unsubscribe_invalid_token(client):
    """Invalid unsubscribe token should return 404."""
    resp = await client.get("/api/unsubscribe/nonexistent-unsub-token")
    assert resp.status_code == 404
    assert "недействительна" in resp.text
