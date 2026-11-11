"""Pydantic schemas for append-only governance and operational audit logs."""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    """Schema representing an immutable audit event record."""

    model_config = ConfigDict(from_attributes=True)

    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Categorical classification of the event")
    action: str = Field(..., description="Action performed, e.g. APPROVE, REJECT, RUN")
    decision: Optional[str] = Field(None, description="Resulting decision if applicable")
    actor_id: str = Field(..., description="User or service identity that performed the action")
    entity_type: str = Field(..., description="Target entity type, e.g. PROPOSAL, WORKFLOW")
    entity_id: str = Field(..., description="Target entity identifier")
    portfolio_id: Optional[str] = Field(None, description="Associated portfolio ID")
    proposal_id: Optional[str] = Field(None, description="Associated proposal ID")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    timestamp: datetime = Field(..., description="Timestamp when event occurred")
    reason: Optional[str] = Field(None, description="Optional rationale or justification")
    metadata_json: Optional[dict[str, Any]] = Field(None, description="Structured contextual metadata")


class AuditListResponse(BaseModel):
    """List response containing ordered audit trail events."""

    events: List[AuditEventResponse] = Field(default_factory=list, description="Chronological audit records")
    total_count: int = Field(..., description="Total count of events retrieved")

