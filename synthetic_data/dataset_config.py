"""Dataset configuration presets and parameters for synthetic data generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetConfig:
    """Configuration parameters for synthetic portfolio dataset generation."""

    name: str
    investor_count: int = 5
    portfolios_per_investor: int = 2
    instrument_count: int = 20
    trading_days: int = 30
    proposals_per_portfolio: int = 1
    trades_per_proposal: int = 2
    min_holdings: int = 3
    max_holdings: int = 8
    seed: int = 20261022
    dataset_reference_date: str = "2026-01-15"
    reproducible_build_timestamp: str = "2026-01-15T00:00:00Z"


STARTER_CONFIG = DatasetConfig(
    name="starter",
    investor_count=5,
    portfolios_per_investor=2,
    instrument_count=20,
    trading_days=30,
    min_holdings=3,
    max_holdings=8,
    proposals_per_portfolio=1,
    trades_per_proposal=2,
    seed=20261022,
)

FULL_CONFIG = DatasetConfig(
    name="full",
    investor_count=500,
    portfolios_per_investor=2,  # 1,000 portfolios
    instrument_count=5000,
    trading_days=250,
    min_holdings=4,             # 1 cash + 4 non-cash = 5 holdings per portfolio
    max_holdings=4,             # Exactly 5,000 holdings across 1,000 portfolios
    proposals_per_portfolio=1,
    trades_per_proposal=2,
    seed=20261022,
)
