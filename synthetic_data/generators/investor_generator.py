"""Deterministic generator for synthetic InvestorProfile records."""

from datetime import datetime, timezone
from typing import Any, Optional
import numpy as np

from synthetic_data.id_generator import generate_investor_id

_FIRST_NAMES = [
    "Avery", "Blake", "Casey", "Dakota", "Emerson", "Finley", "Gray", "Harper",
    "Jordan", "Kendall", "Morgan", "Parker", "Quinn", "Reese", "Riley", "Rowan",
    "Sawyer", "Taylor", "Hayden", "Logan", "Cameron", "Elliot", "Peyton", "Skyler"
]

_LAST_NAMES = [
    "Sterling", "Vanguard", "Meridian", "Horizon", "Pinnacle", "Apex", "Summit",
    "Crest", "Beacon", "Solstice", "Zenith", "Atlas", "Onyx", "Valence", "Solomon",
    "Hartford", "Fairmont", "Kensington", "Wellington", "Evergreen"
]

_RISK_CATEGORIES = ["LOW", "MODERATE", "HIGH"]


def generate_investors(
    count: int,
    seed: int = 20261022,
    base_created_at: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Generate deterministic synthetic investor profile records.

    Args:
        count: Number of investor records to generate.
        seed: Deterministic random seed.
        base_created_at: Base creation timestamp (defaults to 2025-01-01 09:00:00 UTC).

    Returns:
        List of investor profile dictionaries.
    """
    if not isinstance(count, int) or count < 0:
        raise ValueError(f"count must be an integer >= 0, got {count}")

    if count == 0:
        return []

    rng = np.random.default_rng(seed)
    created_base = base_created_at or datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    investors: list[dict[str, Any]] = []

    for i in range(1, count + 1):
        inv_id = generate_investor_id(i)
        first_name = rng.choice(_FIRST_NAMES)
        last_name = rng.choice(_LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        risk_category = rng.choice(_RISK_CATEGORIES)

        investors.append(
            {
                "investor_id": inv_id,
                "name": full_name,
                "risk_category": str(risk_category),
                "created_at": created_base,
            }
        )

    return investors

