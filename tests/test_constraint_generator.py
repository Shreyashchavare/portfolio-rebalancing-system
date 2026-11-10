"""Tests for synthetic constraint generator and bridge associations."""

from datetime import date
from decimal import Decimal

from synthetic_data.generators.constraint_generator import generate_constraints
from synthetic_data.generators.instrument_generator import generate_instruments
from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.validators.schema_validator import SchemaValidator


def _build_test_parents():
    investors = generate_investors(count=3, seed=123)
    portfolios = generate_portfolios(investors, portfolios_per_investor=2, seed=123)
    instruments = generate_instruments(count=20, seed=123)
    return portfolios, instruments


def test_generate_constraints_structure():
    portfolios, instruments = _build_test_parents()
    constraints, bridge = generate_constraints(portfolios, instruments, seed=123)

    assert len(constraints) > 0
    first = constraints[0]
    expected_fields = {
        "constraint_id",
        "constraint_name",
        "constraint_type",
        "scope_type",
        "scope_reference_id",
        "severity",
        "threshold_value",
        "threshold_unit",
        "effective_from",
        "effective_to",
        "is_active",
        "description",
    }
    assert set(first.keys()) == expected_fields
    assert isinstance(first["effective_from"], date)
    assert isinstance(first["is_active"], bool)

    assert len(bridge) > 0
    first_bridge = bridge[0]
    assert set(first_bridge.keys()) == {"constraint_id", "instrument_id"}


def test_generate_constraints_scopes_and_references():
    portfolios, instruments = _build_test_parents()
    portfolio_ids = {p["portfolio_id"] for p in portfolios}
    instrument_ids = {i["instrument_id"] for i in instruments}
    asset_classes = {i["asset_class"] for i in instruments}

    constraints, _ = generate_constraints(portfolios, instruments, seed=123)

    scopes_found = set()
    for c in constraints:
        scope = c["scope_type"]
        scopes_found.add(scope)
        ref_id = c["scope_reference_id"]
        if scope == "PORTFOLIO":
            assert ref_id in portfolio_ids, f"Invalid portfolio scope reference: {ref_id}"
        elif scope == "INSTRUMENT":
            assert ref_id in instrument_ids, f"Invalid instrument scope reference: {ref_id}"
        elif scope == "ASSET_CLASS":
            assert ref_id in asset_classes, f"Invalid asset class scope reference: {ref_id}"
        else:
            raise AssertionError(f"Unknown scope_type: {scope}")

    assert {"PORTFOLIO", "INSTRUMENT", "ASSET_CLASS"}.issubset(scopes_found)


def test_generate_constraints_severities():
    portfolios, instruments = _build_test_parents()
    constraints, _ = generate_constraints(portfolios, instruments, seed=123)
    severities = {c["severity"] for c in constraints}
    assert severities == {"HARD", "SOFT"}


def test_generate_constraints_bridge_table_integrity():
    portfolios, instruments = _build_test_parents()
    constraints, bridge = generate_constraints(portfolios, instruments, seed=123)

    constraint_ids = {c["constraint_id"] for c in constraints}
    instrument_ids = {i["instrument_id"] for i in instruments}

    seen_bridge = set()
    for b in bridge:
        assert b["constraint_id"] in constraint_ids
        assert b["instrument_id"] in instrument_ids
        key = (b["constraint_id"], b["instrument_id"])
        assert key not in seen_bridge, f"Duplicate bridge record: {key}"
        seen_bridge.add(key)


def test_generate_constraints_determinism():
    portfolios, instruments = _build_test_parents()
    c1, b1 = generate_constraints(portfolios, instruments, seed=20261022)
    c2, b2 = generate_constraints(portfolios, instruments, seed=20261022)
    c3, b3 = generate_constraints(portfolios, instruments, seed=99999)

    assert c1 == c2
    assert b1 == b2
    assert c1 != c3


def test_generate_constraints_schema_validation():
    portfolios, instruments = _build_test_parents()
    constraints, bridge = generate_constraints(portfolios, instruments, seed=123)

    validator = SchemaValidator()
    req_res = validator.validate_required_fields(
        constraints,
        [
            "constraint_id",
            "constraint_name",
            "constraint_type",
            "scope_type",
            "scope_reference_id",
            "severity",
            "effective_from",
            "is_active",
        ],
        record_id_field="constraint_id",
    )
    assert req_res.passed

    pk_res = validator.validate_primary_key_uniqueness(constraints, "constraint_id")
    assert pk_res.passed

    scope_res = validator.validate_enum_values(
        constraints, "scope_type", ["PORTFOLIO", "ASSET_CLASS", "INSTRUMENT"]
    )
    assert scope_res.passed

    sev_res = validator.validate_enum_values(constraints, "severity", ["HARD", "SOFT"])
    assert sev_res.passed

    bridge_pk = validator.validate_composite_uniqueness(bridge, ["constraint_id", "instrument_id"])
    assert bridge_pk.passed


def test_generate_constraints_empty_inputs():
    c, b = generate_constraints([], [])
    assert c == []
    assert b == []
