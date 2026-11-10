"""Deterministic generator for synthetic MarketPrice records."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import numpy as np

_BASE_PRICES = {
    "EQUITY": 150.0,
    "DEBT": 100.0,
    "ETF": 220.0,
    "GOLD": 2150.0,
    "CASH": 1.0,
}

_VOLATILITY = {
    "EQUITY": 0.012,
    "DEBT": 0.003,
    "ETF": 0.009,
    "GOLD": 0.008,
    "CASH": 0.0,
}


def _generate_trading_dates(start_date: date, count: int) -> list[date]:
    """Generate business days (Monday-Friday) starting from start_date."""
    dates: list[date] = []
    curr = start_date
    while len(dates) < count:
        if curr.weekday() < 5:
            dates.append(curr)
        curr += timedelta(days=1)
    return dates


def generate_market_prices(
    instruments: list[dict[str, Any]],
    trading_days: int = 250,
    start_date: date = date(2025, 1, 1),
    seed: int = 20261022,
    source: str = "SYNTHETIC",
) -> list[dict[str, Any]]:
    """Generate deterministic synthetic market price records across trading days.

    Args:
        instruments: List of instrument dictionaries containing 'instrument_id' and optional 'asset_class'.
        trading_days: Total number of sequential trading days.
        start_date: Starting calendar date for price series.
        seed: Deterministic random seed.
        source: Provenance label (defaults to 'SYNTHETIC').

    Returns:
        List of market price dictionaries with positive Decimal prices.
    """
    if not isinstance(trading_days, int) or trading_days < 0:
        raise ValueError(f"trading_days must be an integer >= 0, got {trading_days}")

    if not instruments or trading_days == 0:
        return []

    rng = np.random.default_rng(seed)
    trading_dates = _generate_trading_dates(start_date, trading_days)

    prices: list[dict[str, Any]] = []
    record_id = 1

    for inst in instruments:
        inst_id = inst["instrument_id"]
        asset_class = inst.get("asset_class", "EQUITY")
        current_price = _BASE_PRICES.get(asset_class, 100.0)
        vol = _VOLATILITY.get(asset_class, 0.01)

        for price_date in trading_dates:
            # Deterministic geometric random walk return
            if vol > 0:
                ret = rng.normal(0.0003, vol)
                current_price = max(1.0, current_price * (1.0 + ret))

            dec_price = Decimal(f"{current_price:.4f}").quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )

            prices.append(
                {
                    "id": record_id,
                    "instrument_id": inst_id,
                    "price": dec_price,
                    "price_date": price_date,
                    "source": source,
                }
            )
            record_id += 1

    return prices

