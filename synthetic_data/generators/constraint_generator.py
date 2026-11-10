"""Deterministic synthetic policy constraint and bridge association generator."""

from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np

from synthetic_data.id_generator import generate_constraint_id

_CONSTRAINT_TEMPLATES = [
    {
        "name": "Max Single Position Weight",
        "type": "MAX_POSITION_WEIGHT",
        "scope_type": "PORTFOLIO",
        "severity": "HARD",
        "threshold_value": Decimal("25.0000"),
        "threshold_unit": "PERCENT",
        "desc": "Maximum allowed weight for any single asset position in the portfolio.",
    },
    {
        "name": "Minimum Trade Notional Size",
        "type": "MIN_TRADE_VALUE",
        "scope_type": "PORTFOLIO",
        "severity": "SOFT",
        "threshold_value": Decimal("500.0000"),
        "threshold_unit": "USD",
        "desc": "Soft threshold to discourage micro-trades during rebalancing.",
    },
    {
        "name": "Asset Class Liquidity Reserve",
        "type": "LIQUIDITY_LIMIT",
        "scope_type": "ASSET_CLASS",
        "severity": "HARD",
        "threshold_value": Decimal("5.0000"),
        "threshold_unit": "PERCENT",
        "desc": "Minimum mandatory liquidity buffer required in cash or cash-equivalents.",
    },
    {
        "name": "Restricted Trading List",
        "type": "EXCLUDED_INSTRUMENT",
        "scope_type": "INSTRUMENT",
        "severity": "HARD",
        "threshold_value": None,
        "threshold_unit": None,
        "desc": "Mandatory exclusion list barring acquisition of restricted instruments.",
    },
    {
        "name": "Minimum Position Order Quantity",
        "type": "MIN_TRADE_QUANTITY",
        "scope_type": "INSTRUMENT",
        "severity": "SOFT",
        "threshold_value": Decimal("5.0000"),
        "threshold_unit": "UNITS",
        "desc": "Minimum recommended order quantity for fixed income lot constraints.",
    },
]


def generate_constraints(
    portfolios: Sequence[Mapping[str, Any]],
    instruments: Sequence[Mapping[str, Any]],
    seed: Union[int, np.random.Generator] = 20261022,
    effective_from: Optional[date] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate synthetic policy constraints and bridge table associations."""
    if not portfolios or not instruments:
        return [], []

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    eff_from = effective_from or date(2026, 1, 1)

    constraints: list[dict[str, Any]] = []
    bridge_records: list[dict[str, Any]] = []

    c_counter = 1

    # 1. Portfolio-scoped constraints
    for p in portfolios:
        p_id = p["portfolio_id"]
        # MAX_POSITION_WEIGHT
        c_id = generate_constraint_id(c_counter)
        c_counter += 1
        constraints.append(
            {
                "constraint_id": c_id,
                "constraint_name": f"Max Weight - {p_id}",
                "constraint_type": "MAX_POSITION_WEIGHT",
                "scope_type": "PORTFOLIO",
                "scope_reference_id": p_id,
                "severity": "HARD",
                "threshold_value": Decimal("25.0000"),
                "threshold_unit": "PERCENT",
                "effective_from": eff_from,
                "effective_to": None,
                "is_active": True,
                "description": f"Portfolio {p_id} single position cap",
            }
        )

        # MIN_TRADE_VALUE
        c_id = generate_constraint_id(c_counter)
        c_counter += 1
        constraints.append(
            {
                "constraint_id": c_id,
                "constraint_name": f"Min Notional - {p_id}",
                "constraint_type": "MIN_TRADE_VALUE",
                "scope_type": "PORTFOLIO",
                "scope_reference_id": p_id,
                "severity": "SOFT",
                "threshold_value": Decimal("500.0000"),
                "threshold_unit": "USD",
                "effective_from": eff_from,
                "effective_to": None,
                "is_active": True,
                "description": f"Portfolio {p_id} minimum order notional",
            }
        )

    # 2. Asset-Class-scoped constraints
    asset_classes = sorted({i["asset_class"] for i in instruments})
    for ac in asset_classes:
        c_id = generate_constraint_id(c_counter)
        c_counter += 1
        constraints.append(
            {
                "constraint_id": c_id,
                "constraint_name": f"Liquidity Limit - {ac}",
                "constraint_type": "LIQUIDITY_LIMIT",
                "scope_type": "ASSET_CLASS",
                "scope_reference_id": ac,
                "severity": "HARD" if ac == "CASH" else "SOFT",
                "threshold_value": Decimal("5.0000"),
                "threshold_unit": "PERCENT",
                "effective_from": eff_from,
                "effective_to": None,
                "is_active": True,
                "description": f"Liquidity limit for asset class {ac}",
            }
        )

    # 3. Instrument-scoped constraints (EXCLUDED_INSTRUMENT & MIN_TRADE_QUANTITY)
    # Pick a few instruments to exclude deterministically
    inst_pool = [inst for inst in instruments if inst.get("asset_class") != "CASH"]
    if inst_pool:
        # Exclude 1-2 instruments
        num_excluded = min(2, len(inst_pool))
        excluded_indices = rng.choice(len(inst_pool), size=num_excluded, replace=False)

        for e_idx in excluded_indices:
            excl_inst = inst_pool[e_idx]
            inst_id = excl_inst["instrument_id"]
            c_id = generate_constraint_id(c_counter)
            c_counter += 1
            constraints.append(
                {
                    "constraint_id": c_id,
                    "constraint_name": f"Restricted List - {inst_id}",
                    "constraint_type": "EXCLUDED_INSTRUMENT",
                    "scope_type": "INSTRUMENT",
                    "scope_reference_id": inst_id,
                    "severity": "HARD",
                    "threshold_value": None,
                    "threshold_unit": None,
                    "effective_from": eff_from,
                    "effective_to": None,
                    "is_active": True,
                    "description": f"Restricted instrument policy for {inst_id}",
                }
            )
            # Bridge record
            bridge_records.append(
                {
                    "constraint_id": c_id,
                    "instrument_id": inst_id,
                }
            )

        # Min trade quantity for another instrument
        avail_inst = [inst for idx, inst in enumerate(inst_pool) if idx not in excluded_indices]
        if avail_inst:
            min_q_inst = avail_inst[0]
            inst_id = min_q_inst["instrument_id"]
            c_id = generate_constraint_id(c_counter)
            c_counter += 1
            constraints.append(
                {
                    "constraint_id": c_id,
                    "constraint_name": f"Min Order Quantity - {inst_id}",
                    "constraint_type": "MIN_TRADE_QUANTITY",
                    "scope_type": "INSTRUMENT",
                    "scope_reference_id": inst_id,
                    "severity": "SOFT",
                    "threshold_value": Decimal("10.0000"),
                    "threshold_unit": "UNITS",
                    "effective_from": eff_from,
                    "effective_to": None,
                    "is_active": True,
                    "description": f"Minimum order quantity for {inst_id}",
                }
            )
            bridge_records.append(
                {
                    "constraint_id": c_id,
                    "instrument_id": inst_id,
                }
            )

    return constraints, bridge_records

