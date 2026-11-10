"""Deterministic generator for synthetic Portfolio records."""

from datetime import datetime, timezone
from typing import Any, Optional
import numpy as np

from synthetic_data.id_generator import generate_portfolio_id

_STRATEGY_NAMES = [
    "Growth & Income",
    "Balanced Strategic",
    "Capital Preservation",
    "Dynamic Asset Allocation",
    "Global Total Return",
    "Core Multi-Asset",
    "Conservative Liquidity",
    "High Growth Alpha",
]


def generate_portfolios(
    investors: list[dict[str, Any]],
    portfolios_per_investor: int = 1,
    seed: int = 20261022,
    base_currency: str = "USD",
    base_created_at: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Generate deterministic synthetic portfolio records mapped to investors.

    Args:
        investors: List of parent investor dictionaries containing 'investor_id'.
        portfolios_per_investor: Number of portfolios generated per investor.
        seed: Deterministic random seed.
        base_currency: Default portfolio currency (ISO 4217).
        base_created_at: Base creation timestamp (defaults to 2025-01-01 10:00:00 UTC).

    Returns:
        List of portfolio dictionaries.
    """
    if not isinstance(portfolios_per_investor, int) or portfolios_per_investor < 0:
        raise ValueError(
            f"portfolios_per_investor must be an integer >= 0, got {portfolios_per_investor}"
        )

    if not investors or portfolios_per_investor == 0:
        return []

    rng = np.random.default_rng(seed)
    created_base = base_created_at or datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    portfolios: list[dict[str, Any]] = []

    for inv in investors:
        inv_id = inv["investor_id"]
        inv_name = inv.get("name", inv_id)

        for p_idx in range(1, portfolios_per_investor + 1):
            p_id = generate_portfolio_id(inv_id, p_idx)
            strategy = rng.choice(_STRATEGY_NAMES)
            p_name = f"{inv_name} {strategy} {p_idx}" if portfolios_per_investor > 1 else f"{inv_name} {strategy}"

            # 95% ACTIVE, 5% INACTIVE deterministically
            status = "ACTIVE" if rng.random() > 0.05 else "INACTIVE"

            portfolios.append(
                {
                    "portfolio_id": p_id,
                    "investor_id": inv_id,
                    "portfolio_name": p_name,
                    "base_currency": base_currency,
                    "status": status,
                    "created_at": created_base,
                }
            )

    return portfolios

