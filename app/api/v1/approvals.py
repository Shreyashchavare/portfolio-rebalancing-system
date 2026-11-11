"""REST API endpoints for proposal approval governance and durable audit trails."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_reviewer
from app.database.session import get_db
from app.models.rebalance_proposal import RebalanceProposal
from app.schemas.approval import (
    ApprovalDecisionResponse,
    ApproveProposalRequest,
    RejectProposalRequest,
    ReviewerContext,
)
from app.schemas.audit import AuditEventResponse, AuditListResponse
from app.services.approval.approval_service import (
    ApprovalAuthorizationError,
    ApprovalService,
    InvalidProposalStateError,
    InvalidRejectionReasonError,
    ProposalNotFoundError,
    SafetyInterventionRequiredError,
)
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/proposals", tags=["Proposal Governance & Audit"])


@router.post(
    "/{proposal_id}/approve",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a rebalancing proposal",
    description="Authorized reviewer approves an eligible proposal and all executable proposed trades.",
)
def approve_proposal(
    proposal_id: str,
    payload: Optional[ApproveProposalRequest] = None,
    reviewer: ReviewerContext = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    """Approve proposal with authenticated reviewer principal and record atomic audit event."""
    notes = payload.notes if payload else None
    service = ApprovalService(db)
    try:
        return service.approve_proposal(
            proposal_id=proposal_id,
            reviewer=reviewer,
            notes=notes,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidProposalStateError, SafetyInterventionRequiredError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error approving proposal %s: %s", proposal_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during proposal approval.",
        ) from exc


@router.post(
    "/{proposal_id}/reject",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a rebalancing proposal",
    description="Authorized reviewer rejects a proposal with a mandatory non-empty justification.",
)
def reject_proposal(
    proposal_id: str,
    payload: RejectProposalRequest,
    reviewer: ReviewerContext = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
) -> ApprovalDecisionResponse:
    """Reject proposal with mandatory justification reason and record atomic audit event."""
    service = ApprovalService(db)
    try:
        return service.reject_proposal(
            proposal_id=proposal_id,
            reviewer=reviewer,
            reason=payload.reason,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ApprovalAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidProposalStateError, InvalidRejectionReasonError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error rejecting proposal %s: %s", proposal_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during proposal rejection.",
        ) from exc


@router.get(
    "/{proposal_id}/audit",
    response_model=AuditListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve audit trail for a proposal",
    description="Read-only query of all chronological audit events associated with a rebalance proposal.",
)
def get_proposal_audit_events(
    proposal_id: str,
    db: Session = Depends(get_db),
) -> AuditListResponse:
    """Query chronological audit event trail for the specified proposal."""
    proposal = db.query(RebalanceProposal).filter_by(proposal_id=proposal_id).first()
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal '{proposal_id}' was not found.",
        )

    audit_service = AuditService(db)
    events = audit_service.get_events_for_proposal(proposal_id)
    return AuditListResponse(
        events=[AuditEventResponse.model_validate(e) for e in events],
        total_count=len(events),
    )

