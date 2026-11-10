"""Tests for deterministic financial and portfolio calculations."""

from datetime import date
from decimal import Decimal

from synthetic_data.calculations import (
    calculate_allocation_drift,
    calculate_asset_class_weights,
    calculate_portfolio_market_value,
    calculate_position_market_value,
    calculate_trade_fee,
    calculate_trade_notional,
    match_fee_tier,
)


def test_calculate_position_market_value():
    qty = Decimal("100.0000")
    price = Decimal("150.5000")
    val = calculate_position_market_value(qty, price)
    assert val == Decimal("15050.0000")
    assert isinstance(val, Decimal)


def test_calculate_portfolio_market_value():
    positions = [
        {"instrument_id": "INS-000001", "quantity": Decimal("10.0000")},
        {"instrument_id": "INS-000002", "quantity": Decimal("20.0000")},
    ]
    prices = {
        "INS-000001": Decimal("100.0000"),
        "INS-000002": Decimal("50.0000"),
    }
    total = calculate_portfolio_market_value(positions, prices)
    assert total == Decimal("2000.0000")


def test_calculate_asset_class_weights():
    positions = [
        {"instrument_id": "INS-000001", "quantity": Decimal("10.0000")},  # Equity: 1000
        {"instrument_id": "INS-000002", "quantity": Decimal("20.0000")},  # Debt: 1000
    ]
    prices = {
        "INS-000001": Decimal("100.0000"),
        "INS-000002": Decimal("50.0000"),
    }
    instruments = {
        "INS-000001": {"instrument_id": "INS-000001", "asset_class": "EQUITY"},
        "INS-000002": {"instrument_id": "INS-000002", "asset_class": "DEBT"},
    }
    weights = calculate_asset_class_weights(positions, prices, instruments)
    assert weights["EQUITY"] == Decimal("50.0000")
    assert weights["DEBT"] == Decimal("50.0000")
    assert sum(weights.values()) == Decimal("100.0000")


def test_calculate_allocation_drift():
    current_weights = {
        "EQUITY": Decimal("55.0000"),
        "DEBT": Decimal("45.0000"),
    }
    target_weights = {
        "EQUITY": Decimal("50.0000"),
        "DEBT": Decimal("50.0000"),
    }
    drift = calculate_allocation_drift(current_weights, target_weights)
    assert drift["EQUITY"] == Decimal("5.0000")
    assert drift["DEBT"] == Decimal("-5.0000")


def test_calculate_trade_notional():
    qty = Decimal("50.0000")
    price = Decimal("200.0000")
    assert calculate_trade_notional(qty, price) == Decimal("10000.0000")


def test_match_fee_tier_and_calculate_trade_fee():
    tiers = [
        {
            "fee_schedule_id": "FEE-EQ-B-01",
            "asset_class": "EQUITY",
            "trade_side": "BUY",
            "min_trade_value": Decimal("0.0000"),
            "max_trade_value": Decimal("10000.0000"),
            "fee_rate_bps": Decimal("10.0000"),
            "fixed_fee": Decimal("5.0000"),
            "minimum_fee": Decimal("10.0000"),
            "maximum_fee": Decimal("100.0000"),
            "effective_from": date(2026, 1, 1),
            "effective_to": None,
        },
        {
            "fee_schedule_id": "FEE-EQ-B-02",
            "asset_class": "EQUITY",
            "trade_side": "BUY",
            "min_trade_value": Decimal("10000.0000"),
            "max_trade_value": None,
            "fee_rate_bps": Decimal("5.0000"),
            "fixed_fee": Decimal("10.0000"),
            "minimum_fee": Decimal("15.0000"),
            "maximum_fee": Decimal("500.0000"),
            "effective_from": date(2026, 1, 1),
            "effective_to": None,
        },
    ]

    # Test matching tier 1
    tier1 = match_fee_tier(tiers, "EQUITY", "BUY", Decimal("5000.0000"), date(2026, 1, 15))
    assert tier1 is not None
    assert tier1["fee_schedule_id"] == "FEE-EQ-B-01"

    # Fee = fixed (5) + notional (5000) * 10 bps (0.0010) = 5 + 5 = 10.0000
    fee1 = calculate_trade_fee(Decimal("5000.0000"), tier1)
    assert fee1 == Decimal("10.0000")

    # Test min fee clamping: trade_value = 1000 -> 5 + 1 = 6, clamped to minimum_fee = 10
    fee_small = calculate_trade_fee(Decimal("1000.0000"), tier1)
    assert fee_small == Decimal("10.0000")

    # Test matching tier 2 (trade_value = 20000)
    tier2 = match_fee_tier(tiers, "EQUITY", "BUY", Decimal("20000.0000"), date(2026, 1, 15))
    assert tier2 is not None
    assert tier2["fee_schedule_id"] == "FEE-EQ-B-02"
    # Fee = fixed (10) + 20000 * 5 bps (0.0005) = 10 + 10 = 20.0000
    fee2 = calculate_trade_fee(Decimal("20000.0000"), tier2)
    assert fee2 == Decimal("20.0000")


def test_match_fee_tier_no_match():
    tiers = [
        {
            "fee_schedule_id": "FEE-EQ-B-01",
            "asset_class": "EQUITY",
            "trade_side": "BUY",
            "min_trade_value": Decimal("0.0000"),
            "max_trade_value": Decimal("10000.0000"),
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
        }
    ]
    # Wrong side
    assert match_fee_tier(tiers, "EQUITY", "SELL", Decimal("5000.0000"), date(2026, 5, 1)) is None
    # Out of date
    assert match_fee_tier(tiers, "EQUITY", "BUY", Decimal("5000.0000"), date(2025, 5, 1)) is None

