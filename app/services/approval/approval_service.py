"""Approval governance service for controlled human review of rebalancing proposals."""

from datetime import datetime, timezone
import logging
import threading
from typing import Optional
from sqlalchemy.orm import Session

from app.models.rebalance_proposal import ProposalStatus, RebalanceProposal, ReviewDecision
from app.models.trade import Trade, TradeStatus
from app.models.workflow_run import WorkflowRun
from app.schemas.approval import ApprovalDecisionResponse, ReviewerContext
from app.schemas.orchestration import WorkflowStatus
from app.services.audit.audit_service import AuditService

logger = logging.getLogger(__name__)

PERMITTED_APPROVAL_ROLES = {"REVIEWER", "ADMIN", "COMPLIANCE_OFFICER", "PORTFOLIO_MANAGER"}


class ApprovalGovernanceError(Exception):
    """Base exception for approval governance operations."""

    pass


class ProposalNotFoundError(ApprovalGovernanceError):
    """Raised when a specified proposal does not exist."""

    pass


class InvalidProposalStateError(ApprovalGovernanceError):
    """Raised when attempting an illegal transition on a proposal (e.g. approving a rejected proposal)."""

    pass


class InvalidRejectionReasonError(ApprovalGovernanceError):
    """Raised when rejection reason is missing, empty, or whitespace."""

    pass


class SafetyInterventionRequiredError(ApprovalGovernanceError):
    """Raised when safety, policy, or explanation warnings block automatic or unverified approval."""

    pass


class ApprovalAuthorizationError(ApprovalGovernanceError):
    """Raised when reviewer lacks authenticated principal or required permissions."""

    pass


_sqlite_row_lock = threading.RLock()


class ApprovalService:
    """Orchestrates human review decisions, trade state transitions, and atomic audit logging."""

    def __init__(self, session: Session, audit_service: Optional[AuditService] = None) -> None:
        self.session = session
        self.audit_service = audit_service or AuditService(session)

    def _get_proposal_with_lock(self, proposal_id: str) -> RebalanceProposal:
        """Fetch proposal with row-level locking where supported by the dialect."""
        query = self.session.query(RebalanceProposal).filter_by(proposal_id=proposal_id)
        if self.session.bind and self.session.bind.dialect.name != "sqlite":
            query = query.with_for_update()
        proposal = query.first()
        if not proposal:
            raise ProposalNotFoundError(f"Proposal '{proposal_id}' was not found.")
        return proposal

    def approve_proposal(
        self,
        proposal_id: str,
        reviewer: ReviewerContext,
        notes: Optional[str] = None,
    ) -> ApprovalDecisionResponse:
        """Approve an eligible rebalancing proposal and all proposed executable trades atomically.

        Enforces:
        - Reviewer must be authenticated.
        - Proposals in REJECTED state cannot be approved.
        - Hard-blocked or non-executable proposals cannot be approved.
        - Proposals linked to workflows requiring safety intervention cannot be approved.
        - Decision and audit event are persisted atomically in the same database transaction.
        - Holdings, portfolio values, and market prices are NEVER mutated.
        """
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            with _sqlite_row_lock:
                return self._approve_proposal_internal(proposal_id, reviewer, notes)
        return self._approve_proposal_internal(proposal_id, reviewer, notes)

    def _approve_proposal_internal(
        self,
        proposal_id: str,
        reviewer: ReviewerContext,
        notes: Optional[str] = None,
    ) -> ApprovalDecisionResponse:
        if not reviewer or not reviewer.reviewer_id:
            raise ApprovalAuthorizationError("Authenticated reviewer identity is required.")

        if (reviewer.role or "").strip().upper() not in PERMITTED_APPROVAL_ROLES:
            raise ApprovalAuthorizationError(
                f"Reviewer role '{reviewer.role}' is not authorized to approve rebalance proposals."
            )

        proposal = self._get_proposal_with_lock(proposal_id)

        # Idempotent check: already approved
        if (
            proposal.status == ProposalStatus.APPROVED.value
            and proposal.review_decision == ReviewDecision.APPROVED.value
        ):
            logger.info("Proposal %s is already approved; returning existing state.", proposal_id)
            trades = self.session.query(Trade).filter_by(proposal_id=proposal_id).all()
            return ApprovalDecisionResponse(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                review_decision=proposal.review_decision,
                reviewer_id=reviewer.reviewer_id,
                reviewed_at=proposal.reviewed_at or datetime.now(timezone.utc),
                review_reason=proposal.review_reason,
                approved_trade_count=sum(1 for t in trades if t.status == TradeStatus.APPROVED.value),
                rejected_trade_count=sum(1 for t in trades if t.status == TradeStatus.REJECTED.value),
                blocked_trade_count=sum(1 for t in trades if t.status == TradeStatus.BLOCKED.value),
            )

        # Invariant: Rejected proposals cannot be approved
        if (
            proposal.status == ProposalStatus.REJECTED.value
            or proposal.review_decision == ReviewDecision.REJECTED.value
        ):
            raise InvalidProposalStateError(f"Cannot approve a rejected proposal '{proposal_id}'.")

        # Invariant: Hard violations cannot be approved
        if proposal.review_reason and "hard" in proposal.review_reason.lower():
            raise InvalidProposalStateError(
                f"Cannot approve proposal '{proposal_id}' with hard violations: {proposal.review_reason}"
            )

        # Check linked workflow run for unresolved safety interventions
        wf_run = self.session.query(WorkflowRun).filter_by(proposal_id=proposal_id).first()
        if wf_run:
            if (
                wf_run.status == WorkflowStatus.REQUIRES_ATTENTION.value
                or wf_run.error_code in ("POLICY_RETRIEVAL_FAILED", "EXPLANATION_FAILED")
            ):
                raise SafetyInterventionRequiredError(
                    f"Proposal '{proposal_id}' requires safety intervention: linked workflow "
                    f"is in state '{wf_run.status}' (error_code='{wf_run.error_code}')."
                )
            if wf_run.status == WorkflowStatus.REJECTED.value:
                raise InvalidProposalStateError(
                    f"Cannot approve proposal '{proposal_id}': linked workflow is REJECTED."
                )

        try:
            now = datetime.now(timezone.utc)
            proposal.status = ProposalStatus.APPROVED.value
            proposal.review_decision = ReviewDecision.APPROVED.value
            proposal.reviewed_at = now
            if notes:
                proposal.review_reason = notes

            # Atomically update proposed trades to APPROVED; preserve BLOCKED status
            trades = self.session.query(Trade).filter_by(proposal_id=proposal_id).all()
            approved_count = 0
            rejected_count = 0
            blocked_count = 0

            for trade in trades:
                if trade.status == TradeStatus.PROPOSED.value:
                    trade.status = TradeStatus.APPROVED.value
                    approved_count += 1
                elif trade.status == TradeStatus.BLOCKED.value:
                    blocked_count += 1
                elif trade.status == TradeStatus.REJECTED.value:
                    rejected_count += 1
                elif trade.status == TradeStatus.APPROVED.value:
                    approved_count += 1

            if wf_run and wf_run.status == WorkflowStatus.PENDING_HUMAN_REVIEW.value:
                wf_run.status = WorkflowStatus.APPROVED.value
                wf_run.completed_at = now

            # Record audit event atomically
            self.audit_service.record_event(
                event_type="PROPOSAL_REVIEWED",
                action="APPROVE",
                decision="APPROVED",
                actor_id=reviewer.reviewer_id,
                entity_type="PROPOSAL",
                entity_id=proposal.proposal_id,
                portfolio_id=proposal.portfolio_id,
                proposal_id=proposal.proposal_id,
                workflow_id=wf_run.id if wf_run else None,
                reason=notes,
                metadata={
                    "approved_trades": approved_count,
                    "blocked_trades": blocked_count,
                    "rejected_trades": rejected_count,
                    "reviewer_role": reviewer.role,
                },
            )

            self.session.commit()
            return ApprovalDecisionResponse(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                review_decision=proposal.review_decision,
                reviewer_id=reviewer.reviewer_id,
                reviewed_at=now,
                review_reason=proposal.review_reason,
                approved_trade_count=approved_count,
                rejected_trade_count=rejected_count,
                blocked_trade_count=blocked_count,
            )
        except Exception:
            self.session.rollback()
            raise

    def reject_proposal(
        self,
        proposal_id: str,
        reviewer: ReviewerContext,
        reason: str,
    ) -> ApprovalDecisionResponse:
        """Reject an eligible proposal with a mandatory non-empty reason.

        Enforces:
        - Reviewer must be authenticated.
        - Rejection reason must be non-empty and non-whitespace.
        - Proposals in APPROVED state cannot be rejected.
        - All proposed trades transition to REJECTED (blocked trades remain BLOCKED).
        - Decision and audit event are persisted atomically in the same database transaction.
        """
        if self.session.bind and self.session.bind.dialect.name == "sqlite":
            with _sqlite_row_lock:
                return self._reject_proposal_internal(proposal_id, reviewer, reason)
        return self._reject_proposal_internal(proposal_id, reviewer, reason)

    def _reject_proposal_internal(
        self,
        proposal_id: str,
        reviewer: ReviewerContext,
        reason: str,
    ) -> ApprovalDecisionResponse:
        if not reviewer or not reviewer.reviewer_id:
            raise ApprovalAuthorizationError("Authenticated reviewer identity is required.")

        if (reviewer.role or "").strip().upper() not in PERMITTED_APPROVAL_ROLES:
            raise ApprovalAuthorizationError(
                f"Reviewer role '{reviewer.role}' is not authorized to approve rebalance proposals."
            )

        if not reason or not reason.strip():
            raise InvalidRejectionReasonError("Rejection reason must not be empty or whitespace only.")
        clean_reason = reason.strip()

        proposal = self._get_proposal_with_lock(proposal_id)

        # Idempotent check: already rejected
        if (
            proposal.status == ProposalStatus.REJECTED.value
            and proposal.review_decision == ReviewDecision.REJECTED.value
        ):
            logger.info("Proposal %s is already rejected; returning existing state.", proposal_id)
            trades = self.session.query(Trade).filter_by(proposal_id=proposal_id).all()
            return ApprovalDecisionResponse(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                review_decision=proposal.review_decision,
                reviewer_id=reviewer.reviewer_id,
                reviewed_at=proposal.reviewed_at or datetime.now(timezone.utc),
                review_reason=proposal.review_reason,
                approved_trade_count=sum(1 for t in trades if t.status == TradeStatus.APPROVED.value),
                rejected_trade_count=sum(1 for t in trades if t.status == TradeStatus.REJECTED.value),
                blocked_trade_count=sum(1 for t in trades if t.status == TradeStatus.BLOCKED.value),
            )

        # Invariant: Approved proposals cannot be rejected
        if (
            proposal.status == ProposalStatus.APPROVED.value
            or proposal.review_decision == ReviewDecision.APPROVED.value
        ):
            raise InvalidProposalStateError(f"Cannot reject an approved proposal '{proposal_id}'.")

        try:
            now = datetime.now(timezone.utc)
            proposal.status = ProposalStatus.REJECTED.value
            proposal.review_decision = ReviewDecision.REJECTED.value
            proposal.reviewed_at = now
            proposal.review_reason = clean_reason

            trades = self.session.query(Trade).filter_by(proposal_id=proposal_id).all()
            approved_count = 0
            rejected_count = 0
            blocked_count = 0

            for trade in trades:
                if trade.status == TradeStatus.PROPOSED.value:
                    trade.status = TradeStatus.REJECTED.value
                    rejected_count += 1
                elif trade.status == TradeStatus.BLOCKED.value:
                    blocked_count += 1
                elif trade.status == TradeStatus.APPROVED.value:
                    approved_count += 1
                elif trade.status == TradeStatus.REJECTED.value:
                    rejected_count += 1

            wf_run = self.session.query(WorkflowRun).filter_by(proposal_id=proposal_id).first()
            if wf_run:
                wf_run.status = WorkflowStatus.REJECTED.value
                wf_run.completed_at = now

            self.audit_service.record_event(
                event_type="PROPOSAL_REVIEWED",
                action="REJECT",
                decision="REJECTED",
                actor_id=reviewer.reviewer_id,
                entity_type="PROPOSAL",
                entity_id=proposal.proposal_id,
                portfolio_id=proposal.portfolio_id,
                proposal_id=proposal.proposal_id,
                workflow_id=wf_run.id if wf_run else None,
                reason=clean_reason,
                metadata={
                    "approved_trades": approved_count,
                    "blocked_trades": blocked_count,
                    "rejected_trades": rejected_count,
                    "reviewer_role": reviewer.role,
                },
            )

            self.session.commit()
            return ApprovalDecisionResponse(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                review_decision=proposal.review_decision,
                reviewer_id=reviewer.reviewer_id,
                reviewed_at=now,
                review_reason=clean_reason,
                approved_trade_count=approved_count,
                rejected_trade_count=rejected_count,
                blocked_trade_count=blocked_count,
            )
        except Exception:
            self.session.rollback()
            raise
