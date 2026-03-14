"""
Integration tests for /api/suppliers endpoints.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import delete

from backend.models import Supplier

pytestmark = pytest.mark.asyncio


async def test_create_supplier(client):
    resp = await client.post("/api/suppliers", json={
        "company_name": "ООО Тест Поставщик",
        "email": "test_create@test.ru",
        "phone": "+79001111111",
        "categories": ["Гидравлика"],
        "regions": ["Москва"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["company_name"] == "ООО Тест Поставщик"
    assert data["email"] == "test_create@test.ru"
    assert data["source"] == "manual"
    assert data["active"] is True

    # Clean up
    supplier_id = data["id"]
    await client.delete(f"/api/suppliers/{supplier_id}")


async def test_list_suppliers_empty(client):
    resp = await client.get("/api/suppliers")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


async def test_create_and_get_supplier(client):
    """Create, then list and find."""
    resp = await client.post("/api/suppliers", json={
        "company_name": "ООО НайдиМеня",
        "email": "findme@test.ru",
    })
    assert resp.status_code == 200
    sid = resp.json()["id"]

    # List with search
    resp2 = await client.get("/api/suppliers", params={"search": "НайдиМеня"})
    assert resp2.status_code == 200
    found = [s for s in resp2.json()["items"] if s["email"] == "findme@test.ru"]
    assert len(found) >= 1

    # Clean up
    await client.delete(f"/api/suppliers/{sid}")


async def test_update_supplier(client):
    # Create
    resp = await client.post("/api/suppliers", json={
        "company_name": "ООО Обновить",
        "email": "update@test.ru",
    })
    sid = resp.json()["id"]

    # Update
    resp2 = await client.put(f"/api/suppliers/{sid}", json={
        "company_name": "ООО Обновлённый",
        "phone": "+79002222222",
    })
    assert resp2.status_code == 200
    assert resp2.json()["company_name"] == "ООО Обновлённый"
    assert resp2.json()["phone"] == "+79002222222"

    # Clean up
    await client.delete(f"/api/suppliers/{sid}")


async def test_delete_supplier(client):
    # Create
    resp = await client.post("/api/suppliers", json={
        "company_name": "ООО Удалить",
        "email": "delete@test.ru",
    })
    sid = resp.json()["id"]

    # Delete
    resp2 = await client.delete(f"/api/suppliers/{sid}")
    assert resp2.status_code == 200

    # Verify 404
    resp3 = await client.delete(f"/api/suppliers/{sid}")
    assert resp3.status_code == 404


async def test_delete_supplier_not_found(client):
    resp = await client.delete("/api/suppliers/999999")
    assert resp.status_code == 404


async def test_update_supplier_not_found(client):
    resp = await client.put("/api/suppliers/999999", json={
        "company_name": "Не существует",
    })
    assert resp.status_code == 404
