"""Deterministic synthetic holding generator."""

from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np

from synthetic_data.id_generator import generate_holding_id


def generate_holdings(
    portfolios: Sequence[Mapping[str, Any]],
    instruments: Sequence[Mapping[str, Any]],
    as_of_date: Optional[date] = None,
    seed: Union[int, np.random.Generator] = 20261022,
    min_holdings: int = 2,
    max_holdings: int = 8,
) -> list[dict[str, Any]]:
    """Generate synthetic portfolio holding records with deterministic quantities and lot size alignment.

    Cash is held as an explicit holding in a CASH asset-class instrument.
    """
    if not portfolios or not instruments:
        return []

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    effective_date = as_of_date or date(2026, 1, 15)

    cash_instruments = [inst for inst in instruments if inst.get("asset_class") == "CASH"]
    non_cash_instruments = [inst for inst in instruments if inst.get("asset_class") != "CASH"]

    holdings: list[dict[str, Any]] = []

    for portfolio in portfolios:
        p_id = portfolio["portfolio_id"]

        # 1. Mandatory cash position
        if cash_instruments:
            cash_inst = cash_instruments[int(rng.integers(0, len(cash_instruments)))]
            cash_lot = Decimal(str(cash_inst.get("lot_size", "1.0000")))
            # Random cash buffer between 5,000 and 50,000
            cash_units = int(rng.integers(50, 500))
            cash_qty = (Decimal(cash_units) * Decimal("100.0000")).quantize(Decimal("0.0001"))
            holdings.append(
                {
                    "holding_id": generate_holding_id(p_id, cash_inst["instrument_id"]),
                    "portfolio_id": p_id,
                    "instrument_id": cash_inst["instrument_id"],
                    "quantity": cash_qty,
                    "as_of_date": effective_date,
                }
            )

        # 2. Non-cash positions
        if non_cash_instruments:
            # Determine number of holdings for this portfolio
            pool_size = len(non_cash_instruments)
            num_positions = min(pool_size, int(rng.integers(min_holdings, max_holdings + 1)))
            chosen_indices = rng.choice(pool_size, size=num_positions, replace=False)

            for idx in chosen_indices:
                inst = non_cash_instruments[idx]
                inst_id = inst["instrument_id"]
                lot_size = Decimal(str(inst.get("lot_size", "1.0000")))

                # Multiplier between 1 and 200 lots
                multiplier = int(rng.integers(1, 200))
                quantity = (Decimal(multiplier) * lot_size).quantize(Decimal("0.0001"))

                holdings.append(
                    {
                        "holding_id": generate_holding_id(p_id, inst_id),
                        "portfolio_id": p_id,
                        "instrument_id": inst_id,
                        "quantity": quantity,
                        "as_of_date": effective_date,
                    }
                )

    return holdings

