"""Tests for deterministic synthetic data ID generator utilities.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for ID generation before implementation.
"""

import pytest


def _import_id_generator():
    """Dynamically import ID generator functions."""
    from synthetic_data.id_generator import (
        generate_holding_id,
        generate_instrument_id,
        generate_investor_id,
        generate_portfolio_id,
        generate_proposal_id,
    )

    return {
        "generate_investor_id": generate_investor_id,
        "generate_portfolio_id": generate_portfolio_id,
        "generate_instrument_id": generate_instrument_id,
        "generate_holding_id": generate_holding_id,
        "generate_proposal_id": generate_proposal_id,
    }


# ==============================================================================
# Exact Format & Determinism Tests
# ==============================================================================


def test_investor_id_exact_format_and_determinism():
    """Verify investor ID matches INV-000001 format and is deterministic."""
    funcs = _import_id_generator()
    gen = funcs["generate_investor_id"]

    id1 = gen(1)
    id2 = gen(1)
    id42 = gen(42)

    assert id1 == "INV-000001"
    assert id2 == "INV-000001"
    assert id1 == id2, "Identical inputs must produce identical outputs"
    assert id42 == "INV-000042"
    assert gen(999999) == "INV-999999"


def test_portfolio_id_exact_format_and_composition():
    """Verify portfolio ID matches PORT-<investor-id>-01 format."""
    funcs = _import_id_generator()
    gen = funcs["generate_portfolio_id"]

    pid1 = gen("INV-000001", index=1)
    pid2 = gen("INV-000001", index=1)
    pid_alt = gen("INV-000001", index=2)

    assert pid1 == "PORT-INV-000001-01"
    assert pid1 == pid2, "Identical inputs must produce identical outputs"
    assert pid_alt == "PORT-INV-000001-02"
    assert gen("INV-000042", index=9) == "PORT-INV-000042-09"


def test_instrument_id_exact_format_and_determinism():
    """Verify instrument ID matches INS-000001 format."""
    funcs = _import_id_generator()
    gen = funcs["generate_instrument_id"]

    iid1 = gen(1)
    iid2 = gen(1)
    iid10 = gen(10)

    assert iid1 == "INS-000001"
    assert iid1 == iid2
    assert iid10 == "INS-000010"


def test_holding_id_exact_format_and_composition():
    """Verify holding ID matches HOLD-<portfolio-id>-<instrument-id> format."""
    funcs = _import_id_generator()
    gen = funcs["generate_holding_id"]

    hid1 = gen("PORT-INV-000001-01", "INS-000001")
    hid2 = gen("PORT-INV-000001-01", "INS-000001")
    hid_diff = gen("PORT-INV-000001-01", "INS-000002")

    assert hid1 == "HOLD-PORT-INV-000001-01-INS-000001"
    assert hid1 == hid2
    assert hid_diff == "HOLD-PORT-INV-000001-01-INS-000002"
    assert hid1 != hid_diff


def test_proposal_id_exact_format_and_year():
    """Verify proposal ID matches RB-2026-000001 format."""
    funcs = _import_id_generator()
    gen = funcs["generate_proposal_id"]

    prop1 = gen(1, year=2026)
    prop2 = gen(1, year=2026)
    prop_custom = gen(105, year=2026)

    assert prop1 == "RB-2026-000001"
    assert prop1 == prop2
    assert prop_custom == "RB-2026-000105"


# ==============================================================================
# Input Validation & Edge Case Tests
# ==============================================================================


def test_invalid_counter_index_rejected():
    """Verify index <= 0 or invalid types raise ValueError or TypeError."""
    funcs = _import_id_generator()

    with pytest.raises(ValueError):
        funcs["generate_investor_id"](0)

    with pytest.raises(ValueError):
        funcs["generate_investor_id"](-5)

    with pytest.raises(ValueError):
        funcs["generate_portfolio_id"]("INV-000001", index=0)

    with pytest.raises(ValueError):
        funcs["generate_instrument_id"](0)

    with pytest.raises(ValueError):
        funcs["generate_proposal_id"](0)


def test_empty_or_invalid_parent_ids_rejected():
    """Verify empty or non-string referenced IDs raise ValueError."""
    funcs = _import_id_generator()

    with pytest.raises(ValueError):
        funcs["generate_portfolio_id"]("", index=1)

    with pytest.raises(ValueError):
        funcs["generate_holding_id"]("", "INS-000001")

    with pytest.raises(ValueError):
        funcs["generate_holding_id"]("PORT-01", "")

