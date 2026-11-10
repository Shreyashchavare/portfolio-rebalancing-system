"""Tests for deterministic synthetic market price generator."""

from datetime import date
from decimal import Decimal
import pytest

from synthetic_data.validators.schema_validator import SchemaValidator


def _import_market_price_generator():
    """Dynamically import market price generator function."""
    from synthetic_data.generators.market_price_generator import generate_market_prices

    return generate_market_prices


def test_generate_market_prices_count_and_dates():
    """Verify market prices generated for each instrument across requested trading days."""
    gen = _import_market_price_generator()
    instruments = [
        {"instrument_id": "INS-000001", "asset_class": "EQUITY"},
        {"instrument_id": "INS-000002", "asset_class": "DEBT"},
    ]

    trading_days = 10
    prices = gen(
        instruments=instruments,
        trading_days=trading_days,
        start_date=date(2025, 1, 1),
        seed=20261022,
    )

    # 2 instruments * 10 trading days = 20 prices
    assert len(prices) == 20
    for p in prices:
        assert "id" in p
        assert "instrument_id" in p
        assert "price" in p
        assert "price_date" in p
        assert "source" in p
        assert isinstance(p["price"], Decimal)
        assert p["price"] > Decimal("0.0000")
        assert isinstance(p["price_date"], date)
        assert p["source"] == "SYNTHETIC"


def test_generate_market_prices_foreign_keys_and_uniqueness():
    """Verify unique (instrument_id, price_date) pairs and valid instrument foreign keys."""
    gen = _import_market_price_generator()
    instruments = [{"instrument_id": f"INS-{i:06d}", "asset_class": "EQUITY"} for i in range(1, 4)]

    prices = gen(instruments=instruments, trading_days=15, seed=20261022)

    validator = SchemaValidator()
    res_composite = validator.validate_composite_uniqueness(
        records=prices,
        fields=["instrument_id", "price_date"],
    )
    assert res_composite.passed is True

    res_fk = validator.validate_foreign_key_integrity(
        child_records=prices,
        fk_field="instrument_id",
        parent_records=instruments,
        parent_pk_field="instrument_id",
    )
    assert res_fk.passed is True


def test_generate_market_prices_determinism():
    """Verify price paths are deterministic for identical seed."""
    gen = _import_market_price_generator()
    instruments = [{"instrument_id": "INS-000001", "asset_class": "EQUITY"}]

    run1 = gen(instruments=instruments, trading_days=20, seed=20261022)
    run2 = gen(instruments=instruments, trading_days=20, seed=20261022)

    assert run1 == run2


def test_generate_market_prices_full_250_days_support():
    """Verify generator cleanly supports 250 trading days without failure or non-positive prices."""
    gen = _import_market_price_generator()
    instruments = [{"instrument_id": "INS-000001", "asset_class": "EQUITY"}]

    prices = gen(instruments=instruments, trading_days=250, seed=20261022)
    assert len(prices) == 250
    assert all(p["price"] > Decimal("0.0000") for p in prices)


def test_generate_market_prices_empty():
    """Verify empty instruments list produces empty price list."""
    gen = _import_market_price_generator()
    assert gen(instruments=[], trading_days=10) == []
    assert gen(instruments=[{"instrument_id": "INS-1"}], trading_days=0) == []

