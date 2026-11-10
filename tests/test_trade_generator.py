"""Tests for synthetic trade generator."""

from datetime import date
from decimal import Decimal

from synthetic_data.generators.fee_schedule_generator import generate_fee_schedules
from synthetic_data.generators.holding_generator import generate_holdings
from synthetic_data.generators.instrument_generator import generate_instruments
from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.market_price_generator import generate_market_prices
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.generators.rebalance_proposal_generator import generate_rebalance_proposals
from synthetic_data.generators.trade_generator import generate_trades
from synthetic_data.validators.schema_validator import SchemaValidator


def _build_test_context():
    investors = generate_investors(count=3, seed=123)
    portfolios = generate_portfolios(investors, portfolios_per_investor=2, seed=123)
    instruments = generate_instruments(count=20, seed=123)
    market_prices = generate_market_prices(
        instruments, trading_days=10, start_date=date(2026, 1, 1), seed=123
    )
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)
    fee_schedules = generate_fee_schedules()
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=1, seed=123)
    return proposals, holdings, instruments, market_prices, fee_schedules


def test_generate_trades_structure():
    proposals, holdings, instruments, market_prices, fee_schedules = _build_test_context()
    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        seed=123,
    )

    assert len(trades) > 0
    first = trades[0]
    expected_fields = {
        "trade_id",
        "proposal_id",
        "instrument_id",
        "fee_schedule_id",
        "trade_side",
        "quantity",
        "unit_price",
        "trade_value",
        "fee_amount",
        "status",
        "created_at",
    }
    assert set(first.keys()) == expected_fields
    assert isinstance(first["quantity"], Decimal)
    assert isinstance(first["unit_price"], Decimal)
    assert isinstance(first["trade_value"], Decimal)
    assert isinstance(first["fee_amount"], Decimal)


def test_generate_trades_positive_values():
    proposals, holdings, instruments, market_prices, fee_schedules = _build_test_context()
    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        seed=123,
    )

    for t in trades:
        assert t["quantity"] > Decimal("0")
        assert t["unit_price"] > Decimal("0")
        assert t["trade_value"] > Decimal("0")
        assert t["fee_amount"] >= Decimal("0")
        assert t["trade_value"] == (t["quantity"] * t["unit_price"]).quantize(Decimal("0.0001"))


def test_generate_trades_sell_quantity_within_holdings():
    proposals, holdings, instruments, market_prices, fee_schedules = _build_test_context()
    proposal_portfolios = {p["proposal_id"]: p["portfolio_id"] for p in proposals}
    holding_map = {
        (h["portfolio_id"], h["instrument_id"]): h["quantity"] for h in holdings
    }

    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        seed=123,
    )

    for t in trades:
        if t["trade_side"] == "SELL":
            p_id = proposal_portfolios[t["proposal_id"]]
            held_qty = holding_map.get((p_id, t["instrument_id"]), Decimal("0"))
            assert t["quantity"] <= held_qty, (
                f"Valid baseline trade cannot sell more than holding: {t['quantity']} > {held_qty}"
            )


def test_generate_trades_status_coherence_with_proposal():
    proposals, holdings, instruments, market_prices, fee_schedules = _build_test_context()
    proposal_status_map = {p["proposal_id"]: p["status"] for p in proposals}

    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        seed=123,
    )

    for t in trades:
        prop_status = proposal_status_map[t["proposal_id"]]
        if prop_status == "APPROVED":
            assert t["status"] == "APPROVED"
        elif prop_status == "REJECTED":
            assert t["status"] == "REJECTED"
        else:
            assert t["status"] == "PROPOSED"


def test_generate_trades_schema_validation():
    proposals, holdings, instruments, market_prices, fee_schedules = _build_test_context()
    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        seed=123,
    )

    validator = SchemaValidator()
    req_res = validator.validate_required_fields(
        trades,
        [
            "trade_id",
            "proposal_id",
            "instrument_id",
            "trade_side",
            "quantity",
            "unit_price",
            "trade_value",
            "fee_amount",
            "status",
            "created_at",
        ],
        record_id_field="trade_id",
    )
    assert req_res.passed

    pk_res = validator.validate_primary_key_uniqueness(trades, "trade_id")
    assert pk_res.passed

    fk_prop = validator.validate_foreign_key_integrity(
        trades,
        "proposal_id",
        proposals,
        "proposal_id",
        child_id_field="trade_id",
    )
    assert fk_prop.passed

    fk_inst = validator.validate_foreign_key_integrity(
        trades,
        "instrument_id",
        instruments,
        "instrument_id",
        child_id_field="trade_id",
    )
    assert fk_inst.passed

    fk_fee = validator.validate_foreign_key_integrity(
        trades,
        "fee_schedule_id",
        fee_schedules,
        "fee_schedule_id",
        child_id_field="trade_id",
        allow_null=True,
    )
    assert fk_fee.passed
