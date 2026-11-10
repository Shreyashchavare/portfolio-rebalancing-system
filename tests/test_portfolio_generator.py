"""Tests for deterministic synthetic portfolio generator."""

from datetime import datetime
import pytest

from synthetic_data.validators.schema_validator import SchemaValidator


def _import_portfolio_generator():
    """Dynamically import portfolio generator function."""
    from synthetic_data.generators.portfolio_generator import generate_portfolios

    return generate_portfolios


def test_generate_portfolios_count_and_structure():
    """Verify generated portfolio count and required fields."""
    gen = _import_portfolio_generator()
    investors = [
        {"investor_id": "INV-000001", "name": "Investor One"},
        {"investor_id": "INV-000002", "name": "Investor Two"},
    ]

    portfolios = gen(investors=investors, portfolios_per_investor=2, seed=20261022)

    assert len(portfolios) == 4
    for p in portfolios:
        assert "portfolio_id" in p
        assert "investor_id" in p
        assert "portfolio_name" in p
        assert "base_currency" in p
        assert "status" in p
        assert "created_at" in p
        assert isinstance(p["created_at"], datetime)
        assert p["created_at"].tzinfo is not None


def test_generate_portfolios_id_format_and_fk():
    """Verify portfolio IDs adhere to PORT-<investor-id>-01 format and match parent investor."""
    gen = _import_portfolio_generator()
    investors = [{"investor_id": "INV-000001", "name": "Investor One"}]

    portfolios = gen(investors=investors, portfolios_per_investor=2, seed=20261022)

    assert portfolios[0]["portfolio_id"] == "PORT-INV-000001-01"
    assert portfolios[0]["investor_id"] == "INV-000001"
    assert portfolios[1]["portfolio_id"] == "PORT-INV-000001-02"
    assert portfolios[1]["investor_id"] == "INV-000001"


def test_generate_portfolios_determinism():
    """Verify identical inputs and seed produce identical portfolio records."""
    gen = _import_portfolio_generator()
    investors = [{"investor_id": f"INV-{i:06d}", "name": f"User {i}"} for i in range(1, 4)]

    run1 = gen(investors=investors, portfolios_per_investor=1, seed=20261022)
    run2 = gen(investors=investors, portfolios_per_investor=1, seed=20261022)

    assert run1 == run2


def test_generate_portfolios_schema_validation():
    """Verify generated portfolios pass schema validator rules including foreign key check."""
    gen = _import_portfolio_generator()
    investors = [{"investor_id": f"INV-{i:06d}", "name": f"User {i}"} for i in range(1, 5)]

    portfolios = gen(investors=investors, portfolios_per_investor=2, seed=20261022)

    validator = SchemaValidator()
    res_req = validator.validate_required_fields(
        records=portfolios,
        required_fields=["portfolio_id", "investor_id", "portfolio_name", "base_currency", "status", "created_at"],
        record_id_field="portfolio_id",
    )
    assert res_req.passed is True

    res_pk = validator.validate_primary_key_uniqueness(
        records=portfolios,
        pk_field="portfolio_id",
    )
    assert res_pk.passed is True

    res_fk = validator.validate_foreign_key_integrity(
        child_records=portfolios,
        fk_field="investor_id",
        parent_records=investors,
        parent_pk_field="investor_id",
        child_id_field="portfolio_id",
    )
    assert res_fk.passed is True

    res_enum = validator.validate_enum_values(
        records=portfolios,
        field_name="status",
        allowed_values={"ACTIVE", "INACTIVE"},
        record_id_field="portfolio_id",
    )
    assert res_enum.passed is True


def test_generate_portfolios_empty_investors():
    """Verify empty investors list produces empty portfolios without error."""
    gen = _import_portfolio_generator()
    assert gen(investors=[]) == []
    assert gen(investors=[{"investor_id": "INV-1"}], portfolios_per_investor=0) == []

