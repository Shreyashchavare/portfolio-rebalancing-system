"""Deterministic synthetic rebalance proposal generator."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np

from synthetic_data.id_generator import generate_proposal_id

_STATUS_DECISION_PAIRS = [
    ("APPROVED", "APPROVED", "Rebalance strategy aligned with policy and risk category targets."),
    ("APPROVED", "APPROVED", "Routine quarter-end drift correction approved."),
    ("PENDING_REVIEW", "PENDING", None),
    ("DRAFT", "PENDING", None),
    ("REJECTED", "REJECTED", "Rebalance rejected due to proposed trade size exceeding turnover limits."),
]


def generate_rebalance_proposals(
    portfolios: Sequence[Mapping[str, Any]],
    proposals_per_portfolio: int = 1,
    seed: Union[int, np.random.Generator] = 20261022,
    year: int = 2026,
    base_created_at: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Generate synthetic rebalancing proposals with lifecycle consistency."""
    if not portfolios or proposals_per_portfolio < 1:
        return []

    if isinstance(seed, np.random.Generator):
        rng = seed
    else:
        rng = np.random.default_rng(seed)

    base_dt = base_created_at or datetime(year, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    proposals: list[dict[str, Any]] = []
    p_counter = 1

    for portfolio in portfolios:
        p_id = portfolio["portfolio_id"]

        for prop_idx in range(proposals_per_portfolio):
            prop_id = generate_proposal_id(p_counter, year=year)
            p_counter += 1

            # Pick status/decision profile
            pair_idx = int(rng.integers(0, len(_STATUS_DECISION_PAIRS)))
            status, decision, reason = _STATUS_DECISION_PAIRS[pair_idx]

            created_at = base_dt + timedelta(days=prop_idx * 5, hours=int(rng.integers(1, 8)))

            reviewed_at = None
            review_reason = None
            if status in {"APPROVED", "REJECTED"}:
                reviewed_at = created_at + timedelta(hours=int(rng.integers(2, 24)))
                review_reason = reason

            # Pre/post trade estimated portfolio values
            pre_val = (Decimal(int(rng.integers(50000, 250000))) * Decimal("1.0000")).quantize(Decimal("0.0001"))
            # Post value accounts for minimal trade costs / adjustments
            cost_drift = Decimal(int(rng.integers(-50, 50))) * Decimal("1.0000")
            post_val = (pre_val + cost_drift).quantize(Decimal("0.0001"))

            proposals.append(
                {
                    "proposal_id": prop_id,
                    "portfolio_id": p_id,
                    "status": status,
                    "review_decision": decision,
                    "pre_trade_portfolio_value": pre_val,
                    "post_trade_portfolio_value": post_val,
                    "created_at": created_at,
                    "reviewed_at": reviewed_at,
                    "review_reason": review_reason,
                }
            )

    return proposals

