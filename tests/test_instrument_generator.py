"""Tests for deterministic synthetic instrument generator."""

from decimal import Decimal
import pytest

from synthetic_data.validators.schema_validator import SchemaValidator


def _import_instrument_generator():
    """Dynamically import instrument generator function."""
    from synthetic_data.generators.instrument_generator import generate_instruments

    return generate_instruments


def test_generate_instruments_count_and_structure():
    """Verify generated instrument count and required fields."""
    gen = _import_instrument_generator()
    instruments = gen(count=10, seed=20261022)

    assert len(instruments) == 10
    for inst in instruments:
        assert "instrument_id" in inst
        assert "symbol" in inst
        assert "instrument_name" in inst
        assert "asset_class" in inst
        assert "lot_size" in inst
        assert "is_active" in inst
        assert isinstance(inst["lot_size"], Decimal)
        assert inst["lot_size"] > 0
        assert isinstance(inst["is_active"], bool)


def test_generate_instruments_unique_symbols_and_ids():
    """Verify generated symbols and instrument IDs are unique."""
    gen = _import_instrument_generator()
    instruments = gen(count=20, seed=20261022)

    ids = [inst["instrument_id"] for inst in instruments]
    symbols = [inst["symbol"] for inst in instruments]

    assert len(ids) == len(set(ids)), "All instrument IDs must be unique"
    assert len(symbols) == len(set(symbols)), "All symbols must be unique"
    assert ids[0] == "INS-000001"
    assert ids[19] == "INS-000020"


def test_generate_instruments_asset_classes():
    """Verify instruments cover representative asset classes (EQUITY, DEBT, ETF, GOLD, CASH)."""
    gen = _import_instrument_generator()
    instruments = gen(count=25, seed=20261022)

    asset_classes = {inst["asset_class"] for inst in instruments}
    expected_subset = {"EQUITY", "DEBT", "ETF", "GOLD", "CASH"}
    assert expected_subset.issubset(asset_classes), f"Expected {expected_subset} in {asset_classes}"


def test_generate_instruments_determinism():
    """Verify same seed produces identical instruments."""
    gen = _import_instrument_generator()

    run1 = gen(count=15, seed=20261022)
    run2 = gen(count=15, seed=20261022)

    assert run1 == run2


def test_generate_instruments_schema_validation():
    """Verify generated instruments pass schema validator rules."""
    gen = _import_instrument_generator()
    instruments = gen(count=15, seed=20261022)

    validator = SchemaValidator()
    res_req = validator.validate_required_fields(
        records=instruments,
        required_fields=["instrument_id", "symbol", "instrument_name", "asset_class", "lot_size", "is_active"],
        record_id_field="instrument_id",
    )
    assert res_req.passed is True

    res_pk = validator.validate_primary_key_uniqueness(
        records=instruments,
        pk_field="instrument_id",
    )
    assert res_pk.passed is True

    res_num = validator.validate_numeric_bounds(
        records=instruments,
        field_name="lot_size",
        strictly_positive=True,
        record_id_field="instrument_id",
    )
    assert res_num.passed is True


def test_generate_instruments_empty():
    """Verify count=0 produces empty list without error."""
    gen = _import_instrument_generator()
    assert gen(count=0) == []
    with pytest.raises(ValueError):
        gen(count=-5)

