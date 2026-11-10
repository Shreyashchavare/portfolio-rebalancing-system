"""Tests for deterministic synthetic target allocation generator."""

from datetime import date
from decimal import Decimal
import pytest

from synthetic_data.validators.schema_validator import SchemaValidator


def _import_target_allocation_generator():
    """Dynamically import target allocation generator function."""
    from synthetic_data.generators.target_allocation_generator import generate_target_allocations

    return generate_target_allocations


def test_target_allocations_sum_to_exact_100_percent():
    """Verify target allocation weights per portfolio sum to exactly 100.0000%."""
    gen = _import_target_allocation_generator()
    investors = [
        {"investor_id": "INV-000001", "risk_category": "LOW"},
        {"investor_id": "INV-000002", "risk_category": "MODERATE"},
        {"investor_id": "INV-000003", "risk_category": "HIGH"},
    ]
    portfolios = [
        {"portfolio_id": "PORT-INV-000001-01", "investor_id": "INV-000001"},
        {"portfolio_id": "PORT-INV-000002-01", "investor_id": "INV-000002"},
        {"portfolio_id": "PORT-INV-000003-01", "investor_id": "INV-000003"},
    ]

    allocations = gen(portfolios=portfolios, investors=investors, seed=20261022)

    # Group weights by portfolio_id
    weights_by_port: dict[str, Decimal] = {}
    for alloc in allocations:
        pid = alloc["portfolio_id"]
        weights_by_port[pid] = weights_by_port.get(pid, Decimal("0.0000")) + alloc["target_weight"]

    for pid, total_weight in weights_by_port.items():
        assert total_weight == Decimal("100.0000"), (
            f"Portfolio {pid} target weights sum to {total_weight}, expected 100.0000%"
        )


def test_target_allocations_foreign_keys_and_uniqueness():
    """Verify valid portfolio FKs and no duplicate (portfolio_id, asset_class, effective_from)."""
    gen = _import_target_allocation_generator()
    investors = [{"investor_id": "INV-000001", "risk_category": "MODERATE"}]
    portfolios = [{"portfolio_id": "PORT-INV-000001-01", "investor_id": "INV-000001"}]

    allocations = gen(portfolios=portfolios, investors=investors, seed=20261022)

    validator = SchemaValidator()
    res_composite = validator.validate_composite_uniqueness(
        records=allocations,
        fields=["portfolio_id", "asset_class", "effective_from"],
    )
    assert res_composite.passed is True

    res_fk = validator.validate_foreign_key_integrity(
        child_records=allocations,
        fk_field="portfolio_id",
        parent_records=portfolios,
        parent_pk_field="portfolio_id",
    )
    assert res_fk.passed is True


def test_target_allocations_risk_alignment():
    """Verify target allocation weights align with risk profile (e.g. HIGH risk has more EQUITY than LOW risk)."""
    gen = _import_target_allocation_generator()
    investors = [
        {"investor_id": "INV-000001", "risk_category": "LOW"},
        {"investor_id": "INV-000002", "risk_category": "HIGH"},
    ]
    portfolios = [
        {"portfolio_id": "PORT-LOW-01", "investor_id": "INV-000001"},
        {"portfolio_id": "PORT-HIGH-01", "investor_id": "INV-000002"},
    ]

    allocations = gen(portfolios=portfolios, investors=investors, seed=20261022)

    low_equity = next(
        a["target_weight"] for a in allocations if a["portfolio_id"] == "PORT-LOW-01" and a["asset_class"] == "EQUITY"
    )
    high_equity = next(
        a["target_weight"] for a in allocations if a["portfolio_id"] == "PORT-HIGH-01" and a["asset_class"] == "EQUITY"
    )

    assert high_equity > low_equity, (
        f"HIGH risk equity weight ({high_equity}) must exceed LOW risk equity weight ({low_equity})"
    )


def test_target_allocations_schema_validation():
    """Verify generated allocations satisfy all database schema bounds."""
    gen = _import_target_allocation_generator()
    investors = [{"investor_id": "INV-000001", "risk_category": "MODERATE"}]
    portfolios = [{"portfolio_id": "PORT-INV-000001-01", "investor_id": "INV-000001"}]

    allocations = gen(portfolios=portfolios, investors=investors, seed=20261022)

    validator = SchemaValidator()
    res_bounds = validator.validate_numeric_bounds(
        records=allocations,
        field_name="target_weight",
        min_value=Decimal("0.0000"),
        max_value=Decimal("100.0000"),
    )
    assert res_bounds.passed is True

    res_dates = validator.validate_date_ordering(
        records=allocations,
        start_date_field="effective_from",
        end_date_field="effective_to",
        allow_equal=True,
        allow_null_end=True,
    )
    assert res_dates.passed is True


def test_target_allocations_empty():
    """Verify empty inputs return empty allocations without error."""
    gen = _import_target_allocation_generator()
    assert gen(portfolios=[], investors=[]) == []

