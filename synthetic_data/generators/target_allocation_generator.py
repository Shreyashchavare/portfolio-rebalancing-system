"""Deterministic generator for synthetic TargetAllocation records."""

from datetime import date
from decimal import Decimal
from typing import Any, Optional

# Deterministic baseline allocation models based on risk category.
# These models are heuristic baselines for synthetic data demonstration and not financial advice.
_ALLOCATION_MODELS: dict[str, dict[str, Decimal]] = {
    "LOW": {
        "EQUITY": Decimal("20.0000"),
        "DEBT": Decimal("50.0000"),
        "GOLD": Decimal("10.0000"),
        "CASH": Decimal("20.0000"),
    },
    "MODERATE": {
        "EQUITY": Decimal("50.0000"),
        "DEBT": Decimal("30.0000"),
        "ETF": Decimal("10.0000"),
        "CASH": Decimal("10.0000"),
    },
    "HIGH": {
        "EQUITY": Decimal("70.0000"),
        "DEBT": Decimal("10.0000"),
        "ETF": Decimal("15.0000"),
        "CASH": Decimal("5.0000"),
    },
}


def generate_target_allocations(
    portfolios: list[dict[str, Any]],
    investors: list[dict[str, Any]],
    effective_from: date = date(2026, 1, 1),
    effective_to: Optional[date] = None,
    seed: int = 20261022,
) -> list[dict[str, Any]]:
    """Generate deterministic target allocation records per portfolio summing to exactly 100.0000%.

    Args:
        portfolios: List of portfolio dictionaries containing 'portfolio_id' and 'investor_id'.
        investors: List of investor dictionaries containing 'investor_id' and 'risk_category'.
        effective_from: Effective start date for allocation policy.
        effective_to: Optional effective end date.
        seed: Deterministic seed.

    Returns:
        List of target allocation dictionaries with exact Decimal weights.
    """
    if not portfolios or not investors:
        return []

    # Map investor_id -> risk_category
    investor_risk_map = {
        inv["investor_id"]: inv.get("risk_category", "MODERATE")
        for inv in investors
        if "investor_id" in inv
    }

    allocations: list[dict[str, Any]] = []
    record_id = 1

    for port in portfolios:
        port_id = port["portfolio_id"]
        inv_id = port.get("investor_id")
        risk_cat = investor_risk_map.get(inv_id, "MODERATE")

        weights = _ALLOCATION_MODELS.get(risk_cat, _ALLOCATION_MODELS["MODERATE"])

        for asset_class, target_weight in weights.items():
            allocations.append(
                {
                    "id": record_id,
                    "portfolio_id": port_id,
                    "asset_class": asset_class,
                    "target_weight": target_weight,
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                }
            )
            record_id += 1

    return allocations

