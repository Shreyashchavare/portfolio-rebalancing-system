"""Deterministic synthetic fee schedule generator."""

from datetime import date
from decimal import Decimal
from typing import Any, Optional, Sequence

from synthetic_data.id_generator import generate_fee_schedule_id

# Standard tier templates: (min_val, max_val, bps, fixed, min_fee, max_fee)
_TIER_CONFIGS = [
    (Decimal("0.0000"), Decimal("10000.0000"), Decimal("15.0000"), Decimal("5.0000"), Decimal("10.0000"), Decimal("50.0000")),
    (Decimal("10000.0000"), Decimal("100000.0000"), Decimal("10.0000"), Decimal("10.0000"), Decimal("20.0000"), Decimal("200.0000")),
    (Decimal("100000.0000"), None, Decimal("5.0000"), Decimal("25.0000"), Decimal("50.0000"), None),
]

_DEFAULT_ASSET_CLASSES = ["EQUITY", "DEBT", "ETF", "GOLD", "CASH"]
_SIDES = ["BUY", "SELL"]


def generate_fee_schedules(
    asset_classes: Optional[Sequence[str]] = None,
    effective_from: Optional[date] = None,
    effective_to: Optional[date] = None,
    currency: str = "USD",
) -> list[dict[str, Any]]:
    """Generate multi-tiered fee schedules for all asset classes and trading sides."""
    classes = asset_classes or _DEFAULT_ASSET_CLASSES
    eff_from = effective_from or date(2026, 1, 1)

    schedules: list[dict[str, Any]] = []

    for ac in classes:
        for side in _SIDES:
            for tier_idx, (min_val, max_val, bps, fixed, min_fee, max_fee) in enumerate(_TIER_CONFIGS, start=1):
                # Adjust bps slightly based on asset class (e.g. debt is lower cost, cash is 0 bps)
                if ac == "CASH":
                    tier_bps = Decimal("0.0000")
                    tier_fixed = Decimal("0.0000")
                    tier_min = Decimal("0.0000")
                    tier_max = None
                elif ac == "DEBT":
                    tier_bps = (bps * Decimal("0.5")).quantize(Decimal("0.0001"))
                    tier_fixed = fixed
                    tier_min = min_fee
                    tier_max = max_fee
                else:
                    tier_bps = bps
                    tier_fixed = fixed
                    tier_min = min_fee
                    tier_max = max_fee

                sched_id = generate_fee_schedule_id(ac, side, tier_idx)

                schedules.append(
                    {
                        "fee_schedule_id": sched_id,
                        "asset_class": ac,
                        "trade_side": side,
                        "min_trade_value": min_val,
                        "max_trade_value": max_val,
                        "fee_rate_bps": tier_bps,
                        "fixed_fee": tier_fixed,
                        "minimum_fee": tier_min,
                        "maximum_fee": tier_max,
                        "currency": currency,
                        "effective_from": eff_from,
                        "effective_to": effective_to,
                        "is_active": True,
                    }
                )

    return schedules

