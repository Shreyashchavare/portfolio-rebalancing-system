"""Workflow status state machine and transition validation."""

from typing import Any, Optional, Set
from app.schemas.orchestration import InvalidStateTransitionError, WorkflowStatus

TERMINAL_STATES: Set[WorkflowStatus] = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.REJECTED,
    WorkflowStatus.FAILED,
}

ALLOWED_TRANSITIONS: dict[WorkflowStatus, Set[WorkflowStatus]] = {
    WorkflowStatus.RECEIVED: {
        WorkflowStatus.VALIDATING,
        WorkflowStatus.FAILED,
    },
    WorkflowStatus.VALIDATING: {
        WorkflowStatus.ANALYZING,
        WorkflowStatus.FAILED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.ANALYZING: {
        WorkflowStatus.GENERATING_PROPOSAL,
        WorkflowStatus.FAILED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.GENERATING_PROPOSAL: {
        WorkflowStatus.RETRIEVING_POLICIES,
        WorkflowStatus.REJECTED,
        WorkflowStatus.FAILED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.RETRIEVING_POLICIES: {
        WorkflowStatus.GENERATING_EXPLANATION,
        WorkflowStatus.PENDING_HUMAN_REVIEW,
        WorkflowStatus.REJECTED,
        WorkflowStatus.FAILED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.GENERATING_EXPLANATION: {
        WorkflowStatus.PENDING_HUMAN_REVIEW,
        WorkflowStatus.REJECTED,
        WorkflowStatus.FAILED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.PENDING_HUMAN_REVIEW: {
        WorkflowStatus.APPROVED,
        WorkflowStatus.REJECTED,
        WorkflowStatus.REQUIRES_ATTENTION,
    },
    WorkflowStatus.APPROVED: {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
    },
    WorkflowStatus.REQUIRES_ATTENTION: {
        WorkflowStatus.PENDING_HUMAN_REVIEW,
        WorkflowStatus.REJECTED,
        WorkflowStatus.FAILED,
        WorkflowStatus.VALIDATING,
        WorkflowStatus.ANALYZING,
    },
    WorkflowStatus.REJECTED: set(),
    WorkflowStatus.COMPLETED: set(),
    WorkflowStatus.FAILED: set(),
}


def is_terminal(status: WorkflowStatus) -> bool:
    """Check whether a workflow state is terminal."""
    return status in TERMINAL_STATES


def validate_transition(
    current: WorkflowStatus,
    target: WorkflowStatus,
    context: Optional[Any] = None,
) -> None:
    """Validate that moving from current to target state is legally permitted and financially safe.

    Args:
        current: Current workflow status.
        target: Target workflow status.
        context: Optional WorkflowContext providing proposal and constraint findings.

    Raises:
        InvalidStateTransitionError: If the transition is illegal, from a terminal state,
            or violates financial safety invariants (e.g. attempting to approve a rejected proposal).
    """
    if is_terminal(current):
        raise InvalidStateTransitionError(
            f"Cannot transition from terminal workflow status '{current.value}' to '{target.value}'."
        )

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransitionError(
            f"Illegal workflow status transition from '{current.value}' to '{target.value}'. "
            f"Allowed transitions: {[s.value for s in allowed]}"
        )

    # Inviolable Financial Safety Invariant:
    # A rejected or non-executable proposal can NEVER transition to APPROVED.
    if target == WorkflowStatus.APPROVED and context is not None:
        prop = getattr(context, "proposal_result", None)
        if prop is not None:
            status = getattr(prop, "status", None)
            decision = getattr(prop, "review_decision", None)
            is_executable = getattr(prop, "is_executable", True)
            hard_violations = getattr(prop, "hard_violations", None) or getattr(prop, "review_reason", "")

            if status == "REJECTED" or decision == "REJECTED" or not is_executable:
                raise InvalidStateTransitionError(
                    "Financial safety invariant violated: Cannot transition workflow to APPROVED "
                    "when rebalancing proposal is REJECTED or has hard violations."
                )
            if hard_violations and "hard" in str(hard_violations).lower():
                raise InvalidStateTransitionError(
                    "Financial safety invariant violated: Cannot transition workflow to APPROVED "
                    "when rebalance proposal has hard violations."
                )

