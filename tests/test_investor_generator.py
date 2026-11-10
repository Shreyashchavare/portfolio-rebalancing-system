"""Tests for deterministic synthetic investor generator."""

from datetime import datetime, timezone
import pytest

from synthetic_data.validators.schema_validator import SchemaValidator


def _import_investor_generator():
    """Dynamically import investor generator function."""
    from synthetic_data.generators.investor_generator import generate_investors

    return generate_investors


def test_generate_investors_count_and_structure():
    """Verify generated record count, dictionary structure, and required fields."""
    gen = _import_investor_generator()
    investors = gen(count=5, seed=20261022)

    assert len(investors) == 5
    for inv in investors:
        assert "investor_id" in inv
        assert "name" in inv
        assert "risk_category" in inv
        assert "created_at" in inv
        assert isinstance(inv["created_at"], datetime)
        assert inv["created_at"].tzinfo is not None


def test_generate_investors_id_format():
    """Verify generated investor IDs adhere to INV-000001 format."""
    gen = _import_investor_generator()
    investors = gen(count=3, seed=20261022)

    assert investors[0]["investor_id"] == "INV-000001"
    assert investors[1]["investor_id"] == "INV-000002"
    assert investors[2]["investor_id"] == "INV-000003"


def test_generate_investors_determinism():
    """Verify same seed produces identical results and different seed produces variations."""
    gen = _import_investor_generator()

    run1 = gen(count=10, seed=20261022)
    run2 = gen(count=10, seed=20261022)
    run_diff = gen(count=10, seed=99999999)

    assert run1 == run2, "Same seed must produce identical records"
    assert run1 != run_diff, "Different seeds should produce different attributes"


def test_generate_investors_risk_categories_valid():
    """Verify risk categories are drawn only from allowed enum values."""
    gen = _import_investor_generator()
    investors = gen(count=20, seed=20261022)

    allowed = {"LOW", "MODERATE", "HIGH"}
    categories = {inv["risk_category"] for inv in investors}
    assert categories.issubset(allowed)
    # With 20 samples, all categories should be represented
    assert len(categories) > 1


def test_generate_investors_schema_validation():
    """Verify generated investor records pass schema validator checks."""
    gen = _import_investor_generator()
    investors = gen(count=10, seed=20261022)

    validator = SchemaValidator()
    res_req = validator.validate_required_fields(
        records=investors,
        required_fields=["investor_id", "name", "risk_category", "created_at"],
        record_id_field="investor_id",
    )
    assert res_req.passed is True

    res_pk = validator.validate_primary_key_uniqueness(
        records=investors,
        pk_field="investor_id",
    )
    assert res_pk.passed is True

    res_enum = validator.validate_enum_values(
        records=investors,
        field_name="risk_category",
        allowed_values={"LOW", "MODERATE", "HIGH"},
        record_id_field="investor_id",
    )
    assert res_enum.passed is True


def test_generate_investors_empty_and_zero():
    """Verify count=0 produces empty list without error."""
    gen = _import_investor_generator()
    assert gen(count=0) == []
    with pytest.raises(ValueError):
        gen(count=-1)

