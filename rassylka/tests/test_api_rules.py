"""
Integration tests for /api/rules endpoints.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def test_get_rules_autocreate(client):
    """First GET should auto-create default rules."""
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_size"] == 5  # default
    assert data["auto_parse"] is True
    assert data["auto_distribute"] is True
    assert data["matching_sensitivity"] == 0.75


async def test_update_rules(client):
    """PUT should update specified fields only."""
    resp = await client.put("/api/rules", json={
        "batch_size": 10,
        "auto_parse": False,
        "email_delay_seconds": 60,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_size"] == 10
    assert data["auto_parse"] is False
    assert data["email_delay_seconds"] == 60
    # Unchanged fields keep defaults
    assert data["auto_distribute"] is True


async def test_update_rules_sensitivity(client):
    resp = await client.put("/api/rules", json={
        "matching_sensitivity": 0.5,
    })
    assert resp.status_code == 200
    assert resp.json()["matching_sensitivity"] == 0.5


async def test_update_rules_filter_keywords(client):
    resp = await client.put("/api/rules", json={
        "filter_keywords": ["гидромотор", "насос"],
    })
    assert resp.status_code == 200
    kw = resp.json()["filter_keywords"]
    assert "гидромотор" in kw
    assert "насос" in kw
