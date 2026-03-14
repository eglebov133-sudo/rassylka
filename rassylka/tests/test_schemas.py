"""
Unit tests for Pydantic schemas validation.
"""
import pytest
from backend.schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    RoutingRuleUpdate, RoutingRuleResponse,
    BidResponse,
    DashboardStats,
)


class TestSupplierCreate:
    def test_valid_minimal(self):
        s = SupplierCreate(company_name="ООО Тест", email="test@test.ru")
        assert s.company_name == "ООО Тест"
        assert s.email == "test@test.ru"
        assert s.phone == ""
        assert s.categories == []

    def test_valid_full(self):
        s = SupplierCreate(
            company_name="ООО Тест",
            email="test@test.ru",
            phone="+79001234567",
            contact_person="Иван",
            categories=["Гидравлика"],
            regions=["Москва"],
            description="Описание",
            website="https://test.ru",
        )
        assert s.company_name == "ООО Тест"
        assert len(s.categories) == 1

    def test_missing_required(self):
        with pytest.raises(Exception):
            SupplierCreate(email="test@test.ru")  # no company_name


class TestSupplierUpdate:
    def test_partial_update(self):
        u = SupplierUpdate(company_name="Новое название")
        dump = u.model_dump(exclude_unset=True)
        assert dump == {"company_name": "Новое название"}
        assert "email" not in dump

    def test_empty_update(self):
        u = SupplierUpdate()
        dump = u.model_dump(exclude_unset=True)
        assert dump == {}

    def test_toggle_active(self):
        u = SupplierUpdate(active=False)
        dump = u.model_dump(exclude_unset=True)
        assert dump == {"active": False}


class TestRoutingRuleUpdate:
    def test_partial_fields(self):
        r = RoutingRuleUpdate(batch_size=10, auto_parse=False)
        dump = r.model_dump(exclude_unset=True)
        assert dump == {"batch_size": 10, "auto_parse": False}

    def test_sensitivity_range(self):
        r = RoutingRuleUpdate(matching_sensitivity=0.5)
        assert r.matching_sensitivity == 0.5


class TestRoutingRuleResponse:
    def test_all_defaults(self):
        r = RoutingRuleResponse(
            batch_size=5,
            batch_timeout_minutes=30,
            matching_sensitivity=0.75,
            filter_keywords=[],
            auto_parse=True,
            auto_distribute=True,
        )
        assert r.batch_size == 5
        assert r.parse_interval_minutes == 5  # default


class TestDashboardStats:
    def test_construction(self):
        d = DashboardStats(
            total_bids=100,
            active_mailings=5,
            suppliers_notified=50,
            total_suppliers=200,
            response_rate=15.5,
        )
        assert d.total_bids == 100
        assert d.response_rate == 15.5


class TestBidResponse:
    def test_from_dict(self):
        b = BidResponse(
            id=1,
            source_id=12345,
            name="Тест",
            brand="",
            model="",
            year="",
            spare_part_type="",
            count=1,
            delivery_place="",
            description="",
            buyer_name="",
            status="new",
            validity_days=5,
            source_url="https://umit.pro/public-bids/12345",
        )
        assert b.id == 1
        assert b.batch_count == 0  # default
