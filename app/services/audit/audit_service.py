"""Audit service providing durable, append-only recording and read-only retrieval of audit events."""

import logging
import uuid
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


class AuditService:
    """Append-only audit service for recording governance decisions and state transitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record_event(
        self,
        event_type: str,
        action: str,
        actor_id: str,
        entity_type: str,
        entity_id: str,
        decision: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create and stage an append-only AuditEvent within the active database session.

        Does not commit the transaction directly, allowing callers to atomically persist
        state transitions and audit events in a single unit of work.
        """
        event_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            action=action,
            decision=decision,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            portfolio_id=portfolio_id,
            proposal_id=proposal_id,
            workflow_id=workflow_id,
            reason=reason,
            metadata_json=metadata,
        )
        self.session.add(event)
        self.session.flush()
        logger.info(
            "Recorded audit event %s (action=%s, actor=%s, entity=%s:%s)",
            event_id,
            action,
            actor_id,
            entity_type,
            entity_id,
        )
        return event

    def get_events_for_proposal(self, proposal_id: str) -> List[AuditEvent]:
        """Retrieve all audit events for a proposal in chronological order."""
        return (
            self.session.query(AuditEvent)
            .filter_by(proposal_id=proposal_id)
            .order_by(AuditEvent.timestamp.asc())
            .all()
        )

    def get_events_for_portfolio(self, portfolio_id: str) -> List[AuditEvent]:
        """Retrieve all audit events for a portfolio in chronological order."""
        return (
            self.session.query(AuditEvent)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(AuditEvent.timestamp.asc())
            .all()
        )

    def get_events_for_workflow(self, workflow_id: str) -> List[AuditEvent]:
        """Retrieve all audit events for a workflow run in chronological order."""
        return (
            self.session.query(AuditEvent)
            .filter_by(workflow_id=workflow_id)
            .order_by(AuditEvent.timestamp.asc())
            .all()
        )

