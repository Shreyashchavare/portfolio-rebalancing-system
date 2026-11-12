"""Pydantic schemas for portfolio analytics, valuation, and allocation drift."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PortfolioListItem(BaseModel):
    """Summary item for portfolio listing."""

    model_config = ConfigDict(from_attributes=True)

    portfolio_id: str
    investor_id: str
    portfolio_name: str
    base_currency: str
    status: str


class PositionValuation(BaseModel):
    """Valuation details for a single portfolio holding position."""

    model_config = ConfigDict(from_attributes=True)

    holding_id: str
    portfolio_id: str
    instrument_id: str
    symbol: Optional[str] = None
    instrument_name: Optional[str] = None
    asset_class: str
    quantity: Decimal
    unit_price: Decimal
    market_value: Decimal
    price_date: Optional[date] = None
    price_age_days: int = 0
    is_stale: Optional[bool] = None
    diagnostic: Optional[str] = None


class AssetClassAllocation(BaseModel):
    """Actual market value and percentage allocation for an asset class."""

    model_config = ConfigDict(from_attributes=True)

    asset_class: str
    market_value: Decimal
    current_weight: Decimal = Field(..., description="Actual percentage weight [0, 100]")


class AssetClassDrift(BaseModel):
    """Allocation drift comparison for an asset class (actual vs target)."""

    model_config = ConfigDict(from_attributes=True)

    asset_class: str
    current_market_value: Decimal
    target_market_value: Decimal
    current_weight: Decimal = Field(..., description="Actual percentage weight [0, 100]")
    target_weight: Decimal = Field(..., description="Target percentage weight [0, 100]")
    percentage_drift: Decimal = Field(..., description="Current weight minus target weight")
    monetary_drift: Decimal = Field(
        ..., description="Dollar drift = (percentage_drift / 100) * portfolio_value"
    )
    action_signal: Optional[str] = Field(
        default=None, description="Recommended directional signal: BUY, SELL, or HOLD"
    )


class PortfolioValuationResult(BaseModel):
    """Aggregate portfolio valuation outcome."""

    model_config = ConfigDict(from_attributes=True)

    portfolio_id: str
    as_of_date: date
    total_market_value: Decimal
    positions: list[PositionValuation] = Field(default_factory=list)
    asset_classes: list[AssetClassAllocation] = Field(default_factory=list)


class RebalanceTriggerEvaluation(BaseModel):
    """Evaluation of whether a portfolio rebalance is triggered based on configured policies."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        ...,
        description="Status code: TRIGGERED, NOT_TRIGGERED, or NOT_CONFIGURED",
    )
    rebalance_required: Optional[bool] = Field(
        default=None,
        description="True if rebalance is required, False if within policy, None if unconfigured",
    )
    triggered_asset_classes: list[str] = Field(
        default_factory=list,
        description="Asset classes containing positions that breached configured thresholds",
    )
    triggered_positions: list[str] = Field(
        default_factory=list,
        description="Position identifiers (symbols or instrument IDs) that breached configured thresholds",
    )
    policy_description: Optional[str] = Field(
        default=None,
        description="Explanation of policy or lack of configured policy",
    )


class PortfolioDriftResult(BaseModel):
    """Aggregate portfolio drift outcome across all relevant asset classes."""

    model_config = ConfigDict(from_attributes=True)

    portfolio_id: str
    as_of_date: date
    total_market_value: Decimal
    drifts: list[AssetClassDrift] = Field(default_factory=list)
    rebalance_trigger: Optional[RebalanceTriggerEvaluation] = Field(
        default=None,
        description="Deterministic rebalance trigger evaluation against active constraints",
    )

