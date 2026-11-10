"""Deterministic portfolio metrics, allocation drift, and fee calculations."""

from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence


def calculate_position_market_value(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """Calculate the market value of a single holding position.

    Value = Quantity × Market Price.
    """
    return (quantity * unit_price).quantize(Decimal("0.0001"))


def calculate_portfolio_market_value(
    positions: Sequence[Mapping[str, Any]],
    prices_by_instrument: Mapping[str, Decimal],
) -> Decimal:
    """Calculate the total aggregate market value of a portfolio across all positions.

    Cash positions are included via their CASH-class instrument holding.
    """
    total = Decimal("0.0000")
    for pos in positions:
        inst_id = pos["instrument_id"]
        qty = pos["quantity"]
        price = prices_by_instrument.get(inst_id, Decimal("0.0000"))
        total += calculate_position_market_value(qty, price)
    return total.quantize(Decimal("0.0001"))


def calculate_asset_class_weights(
    positions: Sequence[Mapping[str, Any]],
    prices_by_instrument: Mapping[str, Decimal],
    instruments_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Decimal]:
    """Calculate the percentage weight (0 to 100) of each asset class in the portfolio."""
    class_values: dict[str, Decimal] = {}
    total_val = Decimal("0.0000")

    for pos in positions:
        inst_id = pos["instrument_id"]
        qty = pos["quantity"]
        price = prices_by_instrument.get(inst_id, Decimal("0.0000"))
        inst = instruments_by_id.get(inst_id, {})
        ac = inst.get("asset_class", "UNKNOWN")

        pos_val = calculate_position_market_value(qty, price)
        class_values[ac] = class_values.get(ac, Decimal("0.0000")) + pos_val
        total_val += pos_val

    if total_val == Decimal("0.0000"):
        return {ac: Decimal("0.0000") for ac in class_values}

    weights: dict[str, Decimal] = {}
    for ac, val in class_values.items():
        w = ((val / total_val) * Decimal("100.0000")).quantize(Decimal("0.0001"))
        weights[ac] = w

    # Reconcile any small rounding drift so weights sum to exactly 100.0000%
    weight_sum = sum(weights.values())
    drift = Decimal("100.0000") - weight_sum
    if drift != Decimal("0.0000") and weights:
        first_ac = next(iter(weights))
        weights[first_ac] = (weights[first_ac] + drift).quantize(Decimal("0.0001"))

    return weights


def calculate_allocation_drift(
    current_weights: Mapping[str, Decimal],
    target_weights: Mapping[str, Decimal],
) -> dict[str, Decimal]:
    """Calculate allocation drift (Current Weight − Target Weight) per asset class."""
    all_classes = set(current_weights.keys()).union(set(target_weights.keys()))
    drift: dict[str, Decimal] = {}
    for ac in all_classes:
        curr = current_weights.get(ac, Decimal("0.0000"))
        tgt = target_weights.get(ac, Decimal("0.0000"))
        drift[ac] = (curr - tgt).quantize(Decimal("0.0001"))
    return drift


def calculate_trade_notional(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """Calculate trade notional value = Quantity × Unit Price."""
    return (quantity * unit_price).quantize(Decimal("0.0001"))


def match_fee_tier(
    fee_schedules: Sequence[Mapping[str, Any]],
    asset_class: str,
    trade_side: str,
    trade_value: Decimal,
    trade_date: date,
) -> Optional[Mapping[str, Any]]:
    """Find the applicable fee schedule tier matching asset class, side, date, and notional amount."""
    for tier in fee_schedules:
        if tier["asset_class"] != asset_class:
            continue
        if tier["trade_side"] != trade_side:
            continue

        eff_from = tier["effective_from"]
        eff_to = tier.get("effective_to")
        if trade_date < eff_from:
            continue
        if eff_to is not None and trade_date > eff_to:
            continue

        min_val = tier["min_trade_value"]
        max_val = tier.get("max_trade_value")

        if trade_value < min_val:
            continue
        if max_val is not None and trade_value > max_val:
            continue

        return tier

    return None


def calculate_trade_fee(trade_value: Decimal, fee_schedule: Mapping[str, Any]) -> Decimal:
    """Calculate the deterministic trading fee using the applicable fee schedule tier.

    Fee = Fixed Fee + (Trade Value × Fee Rate in bps / 10000), clamped to [min_fee, max_fee].
    """
    fixed = fee_schedule.get("fixed_fee", Decimal("0.0000"))
    bps = fee_schedule.get("fee_rate_bps", Decimal("0.0000"))
    variable = (trade_value * bps / Decimal("10000.0000")).quantize(Decimal("0.0001"))

    fee = fixed + variable

    min_fee = fee_schedule.get("minimum_fee")
    if min_fee is not None and fee < min_fee:
        fee = min_fee

    max_fee = fee_schedule.get("maximum_fee")
    if max_fee is not None and fee > max_fee:
        fee = max_fee

    return fee.quantize(Decimal("0.0001"))

