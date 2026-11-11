"""Pydantic schemas and enums for Grounded Explanation Service & Citations."""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.policy_rag import PolicySearchResult
from app.schemas.portfolio_analytics import AssetClassDrift
from app.schemas.rebalancing import ConstraintFinding, RebalanceProposalResponse


class ExplanationStatus(str, Enum):
    """Execution status classification for generated rebalance explanations."""

    GENERATED = "GENERATED"
    EVIDENCE_ONLY_FALLBACK = "EVIDENCE_ONLY_FALLBACK"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"


class ExplanationCitation(BaseModel):
    """Grounded policy citation with document and chunk identity."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    document_id: str
    policy_family_id: Optional[str] = None
    document_title: str
    version: str
    section_title: Optional[str] = None
    excerpt: str


class TradeExplanationItem(BaseModel):
    """Trade-level explanation strictly grounded in deterministic proposal trades."""

    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    instrument_id: str
    symbol: Optional[str] = None
    trade_side: str
    quantity: Decimal
    unit_price: Decimal
    trade_value: Decimal
    fee_amount: Decimal
    status: str
    explanation: str


class ExplanationRequest(BaseModel):
    """Input payload for generating a grounded rebalance explanation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_id: str
    portfolio_id: str
    proposal_id: str
    as_of_date: date
    proposal: RebalanceProposalResponse
    policy_evidence: List[PolicySearchResult] = Field(default_factory=list)
    drifts: List[AssetClassDrift] = Field(default_factory=list)
    constraint_findings: List[ConstraintFinding] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExplanationResponse(BaseModel):
    """Validated structured explanation output for a rebalancing proposal."""

    model_config = ConfigDict(from_attributes=True)

    workflow_id: str
    portfolio_id: str
    proposal_id: str
    as_of_date: date
    status: ExplanationStatus
    summary: str
    rebalancing_reasons: List[str] = Field(default_factory=list)
    trade_explanations: List[TradeExplanationItem] = Field(default_factory=list)
    allocation_observations: List[str] = Field(default_factory=list)
    policy_findings: List[str] = Field(default_factory=list)
    citations: List[ExplanationCitation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

