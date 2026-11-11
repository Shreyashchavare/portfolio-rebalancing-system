"""Pydantic schemas for deterministic portfolio rebalancing recommendations, simulation, and proposals."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProposedTrade(BaseModel):
    """A single proposed trade recommendation within a rebalancing proposal."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    symbol: Optional[str] = None
    instrument_name: Optional[str] = None
    asset_class: str
    trade_side: str = Field(..., description="BUY or SELL")
    quantity: Decimal = Field(..., description="Quantity to trade (integer multiple of lot size)")
    unit_price: Decimal = Field(..., description="Execution market price as of as_of_date")
    trade_value: Decimal = Field(..., description="Trade notional = quantity * unit_price")
    fee_amount: Decimal = Field(default=Decimal("0.0000"), description="Estimated transaction fee")
    fee_schedule_id: Optional[str] = Field(default=None, description="Matched fee schedule tier reference")
    status: str = Field(default="PROPOSED", description="PROPOSED or BLOCKED")
    diagnostic: Optional[str] = Field(default=None, description="Reason if blocked or informational diagnostic")


class RebalanceRecommendationResult(BaseModel):
    """Aggregate outcome of deterministic trade generation for a portfolio."""

    model_config = ConfigDict(from_attributes=True)

    portfolio_id: str
    as_of_date: date
    starting_portfolio_value: Decimal
    starting_cash: Decimal
    proposed_trades: list[ProposedTrade] = Field(default_factory=list)
    total_sell_notional: Decimal = Decimal("0.0000")
    total_sell_fees: Decimal = Decimal("0.0000")
    total_buy_notional: Decimal = Decimal("0.0000")
    total_buy_fees: Decimal = Decimal("0.0000")
    remaining_cash: Decimal = Decimal("0.0000")
    residual_drifts: dict[str, Decimal] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    validation_failures: list[str] = Field(default_factory=list)
    is_executable: bool = True
    requires_human_review: bool = Field(
        default=False,
        description="True if unknown price freshness, soft constraints, or diagnostics require human review",
    )


class SimulatedPosition(BaseModel):
    """Simulated holding position after applying proposed executable trades."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    symbol: Optional[str] = None
    instrument_name: Optional[str] = None
    asset_class: str
    pre_trade_quantity: Decimal
    post_trade_quantity: Decimal
    unit_price: Decimal
    post_trade_market_value: Decimal
    post_trade_weight: Decimal = Field(..., description="Percentage weight of position in post-trade portfolio")


class SimulatedAllocation(BaseModel):
    """Simulated asset class allocation after applying proposed executable trades."""

    model_config = ConfigDict(from_attributes=True)

    asset_class: str
    post_trade_market_value: Decimal
    post_trade_weight: Decimal = Field(..., description="Percentage weight of asset class in post-trade portfolio")
    target_weight: Decimal
    post_trade_drift: Decimal = Field(..., description="post_trade_weight - target_weight")


class PostTradeSimulationResult(BaseModel):
    """Outcome of isolated in-memory post-trade rebalancing simulation."""

    model_config = ConfigDict(from_attributes=True)

    pre_trade_portfolio_value: Decimal
    post_trade_portfolio_value: Decimal
    pre_trade_cash: Decimal
    post_trade_cash: Decimal
    total_executable_fees: Decimal
    positions: list[SimulatedPosition] = Field(default_factory=list)
    asset_classes: list[SimulatedAllocation] = Field(default_factory=list)
    residual_drifts: dict[str, Decimal] = Field(default_factory=dict)


class ConstraintFinding(BaseModel):
    """Evaluation finding from the policy constraint gatekeeper."""

    model_config = ConfigDict(from_attributes=True)

    constraint_id: str
    constraint_name: str
    constraint_type: str
    severity: str = Field(..., description="HARD or SOFT")
    scope_type: str
    scope_reference_id: str
    threshold_value: Optional[Decimal] = None
    threshold_unit: Optional[str] = None
    is_violated: bool
    affected_instrument_id: Optional[str] = None
    message: str


class TradeResponse(BaseModel):
    """Persisted trade entity returned in rebalancing proposals."""

    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    proposal_id: str
    instrument_id: str
    symbol: Optional[str] = None
    instrument_name: Optional[str] = None
    asset_class: str
    trade_side: str
    quantity: Decimal
    unit_price: Decimal
    trade_value: Decimal
    fee_amount: Decimal
    fee_schedule_id: Optional[str] = None
    status: str
    diagnostic: Optional[str] = None


class RebalanceProposalResponse(BaseModel):
    """Complete rebalancing proposal response including simulation and gatekeeper findings."""

    model_config = ConfigDict(from_attributes=True)

    proposal_id: str
    portfolio_id: str
    as_of_date: date
    status: str = Field(..., description="PENDING_REVIEW, REJECTED, APPROVED, or DRAFT")
    review_decision: str = Field(..., description="PENDING, REJECTED, or APPROVED")
    review_reason: Optional[str] = None
    pre_trade_portfolio_value: Decimal
    post_trade_portfolio_value: Decimal
    created_at: datetime
    trades: list[TradeResponse] = Field(default_factory=list)
    simulation: PostTradeSimulationResult
    constraint_findings: list[ConstraintFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    is_executable: bool = True
    requires_human_review: bool = False


class CreateProposalRequest(BaseModel):
    """Request payload for generating a rebalance proposal."""

    as_of_date: Optional[date] = None
