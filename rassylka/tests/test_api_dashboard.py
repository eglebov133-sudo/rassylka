"""
Integration tests for /api/dashboard endpoints.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_dashboard_stats(client):
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_bids" in data
    assert "active_mailings" in data
    assert "suppliers_notified" in data
    assert "total_suppliers" in data
    assert "response_rate" in data
    assert isinstance(data["total_bids"], int)
    assert isinstance(data["response_rate"], float)


async def test_dashboard_recent(client):
    resp = await client.get("/api/dashboard/recent")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


async def test_dashboard_analytics(client):
    resp = await client.get("/api/dashboard/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "bids_week" in data
    assert "bids_month" in data
    assert "sent_total" in data
    assert "clicked_total" in data
    assert "click_rate" in data
    assert "spam_alert" in data
    assert "top_categories" in data
    assert "top_suppliers" in data
    assert "daily_chart" in data
    assert isinstance(data["daily_chart"], list)
    assert len(data["daily_chart"]) == 14  # 14-day chart
