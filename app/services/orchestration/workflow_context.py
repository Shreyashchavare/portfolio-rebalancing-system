"""Typed context container carrying state across workflow steps."""

from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.explanation import ExplanationResponse
from app.schemas.policy_rag import PolicySearchResult
from app.schemas.portfolio_analytics import PortfolioDriftResult, PortfolioValuationResult
from app.schemas.rebalancing import ConstraintFinding, RebalanceProposalResponse


class WorkflowContext(BaseModel):
    """Isolated, typed context bag passed across workflow execution steps.

    Contains no live database sessions or unrestricted execution tools,
    enforcing clean separation of concerns and immutable data boundaries.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_id: str
    portfolio_id: str
    as_of_date: date
    request_key: str
    policy_query: Optional[str] = None

    # Step outputs
    analytics_valuation: Optional[PortfolioValuationResult] = None
    analytics_drift: Optional[PortfolioDriftResult] = None
    proposal_id: Optional[str] = None
    proposal_result: Optional[RebalanceProposalResponse] = None
    explanation_result: Optional[ExplanationResponse] = None
    policy_evidence: List[PolicySearchResult] = Field(default_factory=list)
    constraint_findings: List[ConstraintFinding] = Field(default_factory=list)

    # Diagnostics and review flags
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    requires_human_review: bool = False

    @property
    def analytics_result(self) -> Optional[PortfolioValuationResult]:
        """Convenience alias for valuation result."""
        return self.analytics_valuation

