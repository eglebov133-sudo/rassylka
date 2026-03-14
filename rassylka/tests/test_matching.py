"""
Unit tests for backend.services.matching.

Tests pure scoring/keyword functions with mock Bid/Supplier objects.
"""
import pytest
from unittest.mock import MagicMock

from backend.services.matching import _extract_keywords, _calculate_match_score


def _make_bid(**kwargs):
    """Create a mock Bid with given attributes."""
    defaults = {
        "name": "",
        "brand": "",
        "model": "",
        "spare_part_type": "",
        "description": "",
        "delivery_place": "",
    }
    defaults.update(kwargs)
    bid = MagicMock()
    for k, v in defaults.items():
        setattr(bid, k, v)
    return bid


def _make_supplier(**kwargs):
    """Create a mock Supplier with given attributes."""
    defaults = {
        "categories": [],
        "regions": [],
        "description": "",
    }
    defaults.update(kwargs)
    supplier = MagicMock()
    for k, v in defaults.items():
        setattr(supplier, k, v)
    return supplier


# ── _extract_keywords ──

class TestExtractKeywords:
    def test_basic_extraction(self):
        bid = _make_bid(
            name="Гидромотор 310.3.112",
            brand="Caterpillar",
            model="320D",
        )
        kw = _extract_keywords(bid)
        assert "гидромотор" in kw
        assert "caterpillar" in kw
        assert "320d" in kw

    def test_short_words_excluded(self):
        """Words of length <= 2 should be excluded."""
        bid = _make_bid(name="не и то большой")
        kw = _extract_keywords(bid)
        assert "не" not in kw
        assert "и" not in kw
        assert "то" not in kw
        assert "большой" in kw

    def test_empty_fields(self):
        bid = _make_bid()
        kw = _extract_keywords(bid)
        assert kw == set()

    def test_none_fields(self):
        bid = _make_bid(name=None, brand=None, description=None)
        kw = _extract_keywords(bid)
        assert kw == set()

    def test_comma_separated(self):
        bid = _make_bid(spare_part_type="фильтры, насосы, шланги")
        kw = _extract_keywords(bid)
        assert "фильтры" in kw
        assert "насосы" in kw
        assert "шланги" in kw


# ── _calculate_match_score ──

class TestCalculateMatchScore:
    def test_perfect_category_match(self):
        bid = _make_bid(
            name="Гидромотор",
            brand="",
            spare_part_type="Гидромоторы",
        )
        supplier = _make_supplier(
            categories=["Гидромоторы", "Гидравлика"],
            regions=[],
            description="",
        )
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        assert score > 0.0

    def test_no_category_overlap(self):
        bid = _make_bid(name="Гидромотор", spare_part_type="Гидромоторы")
        supplier = _make_supplier(
            categories=["Электрика", "Свет"],
            regions=[],
            description="",
        )
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        # No category match, no region match, no brand → low score
        assert score < 0.5

    def test_region_match(self):
        bid = _make_bid(
            name="Деталь",
            delivery_place="Москва",
            brand="",
        )
        supplier = _make_supplier(
            categories=[],
            regions=["Москва", "МО"],
            description="",
        )
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        assert score > 0.2  # region match 0.3

    def test_brand_match(self):
        bid = _make_bid(
            name="Запчасть",
            brand="Komatsu",
        )
        supplier = _make_supplier(
            categories=["Запчасти Komatsu"],
            regions=[],
            description="Поставщик оригинальных запчастей Komatsu",
        )
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        assert score > 0.3  # brand 0.2 + some category

    def test_empty_supplier(self):
        """Supplier with no categories/regions gets a baseline score."""
        bid = _make_bid(name="Деталь")
        supplier = _make_supplier()
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        # Empty supplier: category gives 0.15, region gives 0.1 → 0.25/1.0
        assert 0.0 <= score <= 1.0

    def test_score_in_range(self):
        """Score should always be between 0 and 1."""
        bid = _make_bid(
            name="Запчасть категория",
            brand="TestBrand",
            delivery_place="Москва",
            spare_part_type="Насосы",
        )
        supplier = _make_supplier(
            categories=["Запчасть", "Насосы", "TestBrand"],
            regions=["Москва"],
            description="TestBrand equipment",
        )
        bid_kw = _extract_keywords(bid)
        score = _calculate_match_score(bid, supplier, bid_kw)
        assert 0.0 <= score <= 1.0
