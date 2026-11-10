"""Tests for synthetic holding generator."""

from datetime import date
from decimal import Decimal

from synthetic_data.generators.holding_generator import generate_holdings
from synthetic_data.generators.instrument_generator import generate_instruments
from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.validators.schema_validator import SchemaValidator


def _build_test_parents():
    investors = generate_investors(count=3, seed=123)
    portfolios = generate_portfolios(investors, portfolios_per_investor=2, seed=123)
    instruments = generate_instruments(count=20, seed=123)
    return portfolios, instruments


def test_generate_holdings_record_structure():
    portfolios, instruments = _build_test_parents()
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)

    assert len(holdings) > 0
    first = holdings[0]
    expected_fields = {"holding_id", "portfolio_id", "instrument_id", "quantity", "as_of_date"}
    assert set(first.keys()) == expected_fields
    assert isinstance(first["quantity"], Decimal)
    assert isinstance(first["as_of_date"], date)


def test_generate_holdings_id_format():
    portfolios, instruments = _build_test_parents()
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)

    for h in holdings:
        expected_id = f"HOLD-{h['portfolio_id']}-{h['instrument_id']}"
        assert h["holding_id"] == expected_id


def test_generate_holdings_positive_quantities_and_lot_sizes():
    portfolios, instruments = _build_test_parents()
    instrument_map = {inst["instrument_id"]: inst for inst in instruments}
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)

    for h in holdings:
        assert h["quantity"] > Decimal("0")
        inst = instrument_map[h["instrument_id"]]
        lot_size = inst["lot_size"]
        # Quantity should be an integer multiple of lot size
        ratio = h["quantity"] / lot_size
        assert ratio == ratio.to_integral_value(), f"Quantity {h['quantity']} not multiple of lot size {lot_size}"


def test_generate_holdings_composite_uniqueness():
    portfolios, instruments = _build_test_parents()
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)

    seen = set()
    for h in holdings:
        key = (h["portfolio_id"], h["instrument_id"], h["as_of_date"])
        assert key not in seen, f"Duplicate holding snapshot key: {key}"
        seen.add(key)


def test_generate_holdings_includes_cash_positions():
    portfolios, instruments = _build_test_parents()
    cash_instruments = [i["instrument_id"] for i in instruments if i["asset_class"] == "CASH"]
    assert len(cash_instruments) > 0, "Test requires at least one CASH instrument"

    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)
    portfolio_ids = {p["portfolio_id"] for p in portfolios}

    for p_id in portfolio_ids:
        p_holdings = [h for h in holdings if h["portfolio_id"] == p_id]
        p_cash = [h for h in p_holdings if h["instrument_id"] in cash_instruments]
        assert len(p_cash) >= 1, f"Portfolio {p_id} has no CASH holding"


def test_generate_holdings_exact_five_per_portfolio():
    portfolios, instruments = _build_test_parents()
    # min_holdings=4, max_holdings=4 produces exactly 1 cash + 4 non-cash = 5 holdings per portfolio
    holdings = generate_holdings(
        portfolios,
        instruments,
        as_of_date=date(2026, 1, 15),
        min_holdings=4,
        max_holdings=4,
        seed=123,
    )

    expected_total = len(portfolios) * 5
    assert len(holdings) == expected_total

    instrument_map = {inst["instrument_id"]: inst for inst in instruments}

    for p in portfolios:
        p_id = p["portfolio_id"]
        p_holdings = [h for h in holdings if h["portfolio_id"] == p_id]
        assert len(p_holdings) == 5

        # Check exactly one cash holding
        cash_holdings = [h for h in p_holdings if instrument_map[h["instrument_id"]]["asset_class"] == "CASH"]
        assert len(cash_holdings) == 1

        # Check exactly 4 non-cash holdings
        non_cash = [h for h in p_holdings if instrument_map[h["instrument_id"]]["asset_class"] != "CASH"]
        assert len(non_cash) == 4

        # Check without replacement (distinct instruments within portfolio)
        p_inst_ids = [h["instrument_id"] for h in p_holdings]
        assert len(set(p_inst_ids)) == 5


def test_generate_holdings_determinism():
    portfolios, instruments = _build_test_parents()
    h1 = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=20261022)
    h2 = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=20261022)
    h3 = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=99999)

    assert h1 == h2
    assert [h["quantity"] for h in h1] != [h["quantity"] for h in h3]


def test_generate_holdings_schema_validation():
    portfolios, instruments = _build_test_parents()
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)

    validator = SchemaValidator()
    req_res = validator.validate_required_fields(
        holdings,
        ["holding_id", "portfolio_id", "instrument_id", "quantity", "as_of_date"],
        record_id_field="holding_id",
    )
    assert req_res.passed

    pk_res = validator.validate_primary_key_uniqueness(holdings, "holding_id")
    assert pk_res.passed

    fk_port = validator.validate_foreign_key_integrity(
        holdings,
        "portfolio_id",
        portfolios,
        "portfolio_id",
        child_id_field="holding_id",
    )
    assert fk_port.passed

    fk_inst = validator.validate_foreign_key_integrity(
        holdings,
        "instrument_id",
        instruments,
        "instrument_id",
        child_id_field="holding_id",
    )
    assert fk_inst.passed


def test_generate_holdings_empty_inputs():
    assert generate_holdings([], []) == []
    portfolios, instruments = _build_test_parents()
    assert generate_holdings(portfolios, []) == []
    assert generate_holdings([], instruments) == []
