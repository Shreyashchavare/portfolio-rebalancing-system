"""Deterministic synthetic trade generator."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np

from synthetic_data.calculations import (
    calculate_trade_fee,
    calculate_trade_notional,
    match_fee_tier,
)
from synthetic_data.id_generator import generate_trade_id


def generate_trades(
    proposals: Sequence[Mapping[str, Any]],
    holdings: Sequence[Mapping[str, Any]],
    instruments: Sequence[Mapping[str, Any]],
    market_prices: Sequence[Mapping[str, Any]],
    fee_schedules: Sequence[Mapping[str, Any]],
    constraints: Optional[Sequence[Mapping[str, Any]]] = None,
    seed: Union[int, np.random.Generator] = 20261022,
    trades_per_proposal: int = 2,
) -> list[dict[str, Any]]:
    """Generate synthetic trades linked to rebalance proposals and compliant with holdings/fees/constraints."""
    if not proposals or not instruments or not market_prices:
        return []

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    # Index latest price per instrument
    latest_prices: dict[str, Decimal] = {}
    for p in market_prices:
        inst_id = p["instrument_id"]
        latest_prices[inst_id] = p["price"]

    instrument_map = {inst["instrument_id"]: inst for inst in instruments}

    # Filter out active excluded instruments from baseline BUY recommendations
    excluded_inst_ids = set()
    if constraints:
        for c in constraints:
            if c.get("constraint_type") == "EXCLUDED_INSTRUMENT" and c.get("is_active", True):
                excluded_inst_ids.add(c.get("scope_reference_id"))

    allowed_buy_instruments = [
        inst for inst in instruments
        if inst.get("asset_class") != "CASH" and inst["instrument_id"] not in excluded_inst_ids
    ]
    if not allowed_buy_instruments:
        allowed_buy_instruments = [inst for inst in instruments if inst.get("asset_class") != "CASH"]

    trades: list[dict[str, Any]] = []
    trade_counter = 1

    for prop in proposals:
        prop_id = prop["proposal_id"]
        p_id = prop["portfolio_id"]
        prop_status = prop["status"]
        prop_dt = prop["created_at"]
        trade_date = prop_dt.date() if hasattr(prop_dt, "date") else date(2026, 1, 15)

        # Status coherence: APPROVED -> APPROVED, REJECTED -> REJECTED, otherwise PROPOSED
        if prop_status == "APPROVED":
            trade_status = "APPROVED"
        elif prop_status == "REJECTED":
            trade_status = "REJECTED"
        else:
            trade_status = "PROPOSED"

        # Existing held non-cash instruments for this portfolio
        existing_held = [
            (h["instrument_id"], h["quantity"])
            for h in holdings
            if h["portfolio_id"] == p_id and instrument_map.get(h["instrument_id"], {}).get("asset_class") != "CASH"
        ]

        for t_idx in range(trades_per_proposal):
            if t_idx % 2 == 0 and existing_held:
                side = "SELL"
                inst_id, held_qty = existing_held[int(rng.integers(0, len(existing_held)))]
                lot_size = instrument_map[inst_id]["lot_size"]

                max_lots = int(held_qty // lot_size)
                if max_lots >= 2:
                    sell_lots = int(rng.integers(1, max_lots))
                else:
                    sell_lots = 1
                qty = (Decimal(sell_lots) * lot_size).quantize(Decimal("0.0001"))
                if qty > held_qty:
                    qty = held_qty
            else:
                side = "BUY"
                inst = allowed_buy_instruments[int(rng.integers(0, len(allowed_buy_instruments)))]
                inst_id = inst["instrument_id"]
                lot_size = inst["lot_size"]
                buy_lots = int(rng.integers(5, 50))
                qty = (Decimal(buy_lots) * lot_size).quantize(Decimal("0.0001"))

            unit_price = latest_prices.get(inst_id, Decimal("100.0000"))
            trade_value = calculate_trade_notional(qty, unit_price)

            inst_meta = instrument_map.get(inst_id, {})
            ac = inst_meta.get("asset_class", "EQUITY")

            matched_tier = match_fee_tier(fee_schedules, ac, side, trade_value, trade_date)
            if matched_tier:
                fee_id = matched_tier["fee_schedule_id"]
                fee_amount = calculate_trade_fee(trade_value, matched_tier)
            else:
                fee_id = None
                fee_amount = Decimal("0.0000")

            t_id = generate_trade_id(trade_counter)
            trade_counter += 1

            created_at = prop_dt + timedelta(minutes=int(rng.integers(1, 30)))

            trades.append(
                {
                    "trade_id": t_id,
                    "proposal_id": prop_id,
                    "instrument_id": inst_id,
                    "fee_schedule_id": fee_id,
                    "trade_side": side,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "trade_value": trade_value,
                    "fee_amount": fee_amount,
                    "status": trade_status,
                    "created_at": created_at,
                }
            )

    return trades
