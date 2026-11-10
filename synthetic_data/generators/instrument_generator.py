"""Deterministic generator for synthetic Instrument catalog records."""

from decimal import Decimal
from typing import Any
import numpy as np

from synthetic_data.id_generator import generate_instrument_id

_BASELINE_CATALOG = [
    # EQUITIES
    {"symbol": "EQ-US-LC", "name": "US Large Cap Equity Index", "asset_class": "EQUITY", "lot_size": Decimal("1.0000")},
    {"symbol": "EQ-US-TECH", "name": "US Technology Growth Equities", "asset_class": "EQUITY", "lot_size": Decimal("1.0000")},
    {"symbol": "EQ-EM-VAL", "name": "Emerging Markets Value Equities", "asset_class": "EQUITY", "lot_size": Decimal("1.0000")},
    {"symbol": "EQ-GL-DIV", "name": "Global High Dividend Equity", "asset_class": "EQUITY", "lot_size": Decimal("1.0000")},
    {"symbol": "EQ-EU-CORE", "name": "European Core Blend Equities", "asset_class": "EQUITY", "lot_size": Decimal("1.0000")},
    # DEBT / FIXED INCOME
    {"symbol": "DB-US-UST", "name": "US Treasury 7-10Y Benchmark", "asset_class": "DEBT", "lot_size": Decimal("10.0000")},
    {"symbol": "DB-US-IG", "name": "Investment Grade Corporate Bond", "asset_class": "DEBT", "lot_size": Decimal("10.0000")},
    {"symbol": "DB-GL-SOV", "name": "Global Sovereign Aggregate Debt", "asset_class": "DEBT", "lot_size": Decimal("10.0000")},
    {"symbol": "DB-US-ST", "name": "Short-Term Treasury Bills", "asset_class": "DEBT", "lot_size": Decimal("10.0000")},
    {"symbol": "DB-EM-LOC", "name": "Emerging Local Currency Debt", "asset_class": "DEBT", "lot_size": Decimal("10.0000")},
    # ETFS
    {"symbol": "ETF-WLD-500", "name": "Global 500 Market Index ETF", "asset_class": "ETF", "lot_size": Decimal("1.0000")},
    {"symbol": "ETF-ESG-GL", "name": "Global Sustainable Leader ETF", "asset_class": "ETF", "lot_size": Decimal("1.0000")},
    {"symbol": "ETF-SEMI", "name": "Semiconductor Innovation ETF", "asset_class": "ETF", "lot_size": Decimal("1.0000")},
    {"symbol": "ETF-REIT", "name": "Global Real Estate Income ETF", "asset_class": "ETF", "lot_size": Decimal("1.0000")},
    {"symbol": "ETF-INFRA", "name": "Global Infrastructure ETF", "asset_class": "ETF", "lot_size": Decimal("1.0000")},
    # COMMODITIES & GOLD
    {"symbol": "GLD-PHYS", "name": "Physical Gold Bullion Trust", "asset_class": "GOLD", "lot_size": Decimal("1.0000")},
    {"symbol": "GLD-BARS", "name": "Allocated Sovereign Gold ETC", "asset_class": "GOLD", "lot_size": Decimal("1.0000")},
    # CASH & MONEY MARKET
    {"symbol": "CSH-USD-MM", "name": "USD Treasury Money Market Fund", "asset_class": "CASH", "lot_size": Decimal("1.0000")},
    {"symbol": "CSH-OVR-NT", "name": "Overnight Government Repo Cash", "asset_class": "CASH", "lot_size": Decimal("1.0000")},
    {"symbol": "CSH-EUR-MM", "name": "EUR Liquidity Prime Reserve", "asset_class": "CASH", "lot_size": Decimal("1.0000")},
]

_ASSET_CLASSES = ["EQUITY", "DEBT", "ETF", "GOLD", "CASH"]


def generate_instruments(
    count: int = 20,
    seed: int = 20261022,
) -> list[dict[str, Any]]:
    """Generate deterministic synthetic financial instruments across core asset classes.

    Args:
        count: Total number of instruments to generate.
        seed: Deterministic random seed.

    Returns:
        List of instrument dictionaries.
    """
    if not isinstance(count, int) or count < 0:
        raise ValueError(f"count must be an integer >= 0, got {count}")

    if count == 0:
        return []

    instruments: list[dict[str, Any]] = []

    # First take from baseline catalog
    for idx in range(1, count + 1):
        inst_id = generate_instrument_id(idx)

        if idx <= len(_BASELINE_CATALOG):
            template = _BASELINE_CATALOG[idx - 1]
            symbol = template["symbol"]
            name = template["name"]
            asset_class = template["asset_class"]
            lot_size = template["lot_size"]
        else:
            # Deterministically cycle and generate beyond baseline catalog
            ac = _ASSET_CLASSES[(idx - 1) % len(_ASSET_CLASSES)]
            code = ac[:2] if ac != "GOLD" else "GL"
            symbol = f"{code}-{idx:04d}"
            name = f"Synthetic {ac.capitalize()} Asset {idx}"
            asset_class = ac
            lot_size = Decimal("10.0000") if ac == "DEBT" else Decimal("1.0000")

        instruments.append(
            {
                "instrument_id": inst_id,
                "symbol": symbol,
                "instrument_name": name,
                "asset_class": asset_class,
                "lot_size": lot_size,
                "is_active": True,
            }
        )

    return instruments

