"""
Unit tests for backend.services.bid_parser.

Tests pure functions: _extract_text, parse_bid_data.
No database or network access needed.
"""
import pytest
from backend.services.bid_parser import _extract_text, parse_bid_data


# ── _extract_text ──

class TestExtractText:
    def test_string_input(self):
        assert _extract_text("hello") == "hello"

    def test_none_input(self):
        assert _extract_text(None) == ""

    def test_dict_with_name(self):
        assert _extract_text({"id": 5, "name": "Москва"}) == "Москва"

    def test_dict_without_name(self):
        assert _extract_text({"id": 5}) == ""

    def test_dict_with_none_name(self):
        assert _extract_text({"id": 5, "name": None}) == ""

    def test_integer_input(self):
        assert _extract_text(123) == "123"


# ── parse_bid_data ──

class TestParseBidData:
    def test_full_item(self):
        item = {
            "id": 12345,
            "name": "Гидромотор 310.3.112",
            "technique_card": {
                "car": {
                    "brand": {"id": 1, "name": "Caterpillar"},
                    "model": {"id": 2, "name": "320D"},
                    "year": 2018,
                },
                "special_vehicle": None,
            },
            "spare_part_type": {"id": 18, "name": "Гидромоторы"},
            "count": 3,
            "delivery_place": {"name": "Москва"},
            "description": "Требуется срочно",
            "buyer_name": "ООО Стройтех",
            "delivery_method": "Доставка",
            "taxation": "НДС 20%",
            "relevance_in_days": 7,
        }
        result = parse_bid_data(item)
        assert result["source_id"] == 12345
        assert result["name"] == "Гидромотор 310.3.112"
        assert result["brand"] == "Caterpillar"
        assert result["model"] == "320D"
        assert result["year"] == "2018"
        assert result["spare_part_type"] == "Гидромоторы"
        assert result["count"] == 3
        assert result["delivery_place"] == "Москва"
        assert result["description"] == "Требуется срочно"
        assert result["buyer_name"] == "ООО Стройтех"
        assert result["validity_days"] == 7
        assert "12345" in result["source_url"]

    def test_minimal_item(self):
        item = {"id": 1, "name": "Деталь"}
        result = parse_bid_data(item)
        assert result["source_id"] == 1
        assert result["name"] == "Деталь"
        assert result["brand"] == ""
        assert result["model"] == ""
        assert result["year"] == ""
        assert result["count"] == 1
        assert result["validity_days"] == 5  # default

    def test_special_vehicle_fallback(self):
        """When car is empty, should use special_vehicle data."""
        item = {
            "id": 2,
            "name": "Запчасть",
            "technique_card": {
                "car": {},
                "special_vehicle": {
                    "brand": {"name": "Komatsu"},
                    "model": {"name": "PC200"},
                    "year": 2020,
                },
            },
        }
        result = parse_bid_data(item)
        assert result["brand"] == "Komatsu"
        assert result["model"] == "PC200"
        assert result["year"] == "2020"

    def test_spare_part_type_as_string(self):
        item = {"id": 3, "name": "test", "spare_part_type": "Фильтры"}
        result = parse_bid_data(item)
        assert result["spare_part_type"] == "Фильтры"

    def test_spare_part_type_as_dict(self):
        item = {"id": 4, "name": "test", "spare_part_type": {"id": 5, "name": "Шланги"}}
        result = parse_bid_data(item)
        assert result["spare_part_type"] == "Шланги"

    def test_delivery_place_as_dict(self):
        item = {"id": 5, "name": "test", "delivery_place": {"name": "Краснодар"}}
        result = parse_bid_data(item)
        assert result["delivery_place"] == "Краснодар"

    def test_null_technique_card(self):
        item = {"id": 6, "name": "test", "technique_card": None}
        result = parse_bid_data(item)
        assert result["brand"] == ""
        assert result["model"] == ""

    def test_empty_technique_card(self):
        item = {"id": 7, "name": "test", "technique_card": {}}
        result = parse_bid_data(item)
        assert result["brand"] == ""
        assert result["model"] == ""
