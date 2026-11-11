"""Pydantic schemas and enums for Phase 6 Workflow Orchestration."""

from datetime import date, datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.explanation import ExplanationResponse
from app.schemas.policy_rag import PolicySearchResult
from app.schemas.rebalancing import RebalanceProposalResponse


class WorkflowStatus(str, Enum):
    """Lifecycle states of an orchestrated rebalancing workflow run."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    ANALYZING = "ANALYZING"
    GENERATING_PROPOSAL = "GENERATING_PROPOSAL"
    RETRIEVING_POLICIES = "RETRIEVING_POLICIES"
    GENERATING_EXPLANATION = "GENERATING_EXPLANATION"
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REQUIRES_ATTENTION = "REQUIRES_ATTENTION"


# Custom Exceptions
class WorkflowOrchestrationError(Exception):
    """Base exception for workflow orchestration failures."""

    pass


class IdempotencyConflictError(WorkflowOrchestrationError):
    """Raised when an idempotency key is reused with differing request data."""

    pass


class InvalidStateTransitionError(WorkflowOrchestrationError):
    """Raised when an illegal or blocked state transition is attempted."""

    pass


class WorkflowExecutionError(WorkflowOrchestrationError):
    """Raised when an unrecoverable failure occurs during step execution."""

    def __init__(self, message: str, error_code: str = "EXECUTION_FAILED") -> None:
        super().__init__(message)
        self.error_code = error_code


# Request & Response Schemas
class WorkflowRequest(BaseModel):
    """Input payload to initiate an orchestrated portfolio rebalance workflow."""

    portfolio_id: str = Field(..., description="Target portfolio identifier")
    as_of_date: Optional[date] = Field(None, description="As-of evaluation date (defaults to today)")
    request_key: str = Field(..., min_length=1, max_length=100, description="Idempotency key")
    policy_query: Optional[str] = Field(None, description="Optional custom query for policy retrieval")


class WorkflowResponse(BaseModel):
    """Structured response detailing the state and results of a rebalance workflow run."""

    model_config = ConfigDict(from_attributes=True)

    workflow_id: str = Field(..., description="Unique workflow run identifier")
    portfolio_id: str = Field(..., description="Target portfolio identifier")
    as_of_date: date = Field(..., description="As-of evaluation date")
    status: str = Field(..., description="Current WorkflowStatus")
    request_key: str = Field(..., description="Idempotency key")
    proposal_id: Optional[str] = Field(None, description="Associated rebalance proposal ID")
    proposal: Optional[RebalanceProposalResponse] = Field(None, description="Generated proposal details")
    explanation: Optional[ExplanationResponse] = Field(None, description="Generated grounded explanation")
    policy_evidence: List[PolicySearchResult] = Field(default_factory=list, description="Retrieved policy chunks")
    warnings: List[str] = Field(default_factory=list, description="Diagnostics or compliance warnings")
    errors: List[str] = Field(default_factory=list, description="Logged execution errors")
    requires_human_review: bool = Field(False, description="Flag indicating human approval/review is required")
    error_code: Optional[str] = Field(None, description="Standardized error classification if failed")
    error_message: Optional[str] = Field(None, description="Sanitized diagnostic message if failed")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
