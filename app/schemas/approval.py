"""Pydantic schemas for proposal approval and rejection governance."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewerContext(BaseModel):
    """Authenticated reviewer principal derived from request authorization."""

    reviewer_id: str = Field(..., min_length=1, description="Unique reviewer identifier")
    role: str = Field("REVIEWER", description="Role/permissions tier of the reviewer")
    email: Optional[str] = Field(None, description="Optional reviewer email address")


class ApproveProposalRequest(BaseModel):
    """Payload for approving an eligible rebalancing proposal."""

    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional approval rationale or notes",
    )


class RejectProposalRequest(BaseModel):
    """Payload for rejecting a rebalancing proposal with a mandatory non-empty reason."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mandatory explanation for proposal rejection",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Rejection reason must not be empty or whitespace only.")
        return v.strip()


class ApprovalDecisionResponse(BaseModel):
    """Structured response summarizing the human review decision and affected trade counts."""

    model_config = ConfigDict(from_attributes=True)

    proposal_id: str = Field(..., description="Target rebalance proposal ID")
    status: str = Field(..., description="Updated ProposalStatus (e.g. APPROVED or REJECTED)")
    review_decision: str = Field(..., description="Review decision state (e.g. APPROVED or REJECTED)")
    reviewer_id: str = Field(..., description="Identifier of the authenticated reviewer who made the decision")
    reviewed_at: datetime = Field(..., description="Timestamp of the decision")
    review_reason: Optional[str] = Field(None, description="Rejection reason or approval notes")
    approved_trade_count: int = Field(0, description="Count of trades transitioned to APPROVED")
    rejected_trade_count: int = Field(0, description="Count of trades transitioned to REJECTED")
    blocked_trade_count: int = Field(0, description="Count of trades retained in BLOCKED status")

