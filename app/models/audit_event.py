"""AuditEvent SQLAlchemy entity for append-only governance and operational audit logs."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.rebalance_proposal import RebalanceProposal
    from app.models.workflow_run import WorkflowRun


class AuditEvent(Base):
    """Immutable, append-only record of a governance decision or significant system event."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    portfolio_id: Mapped[Optional[str]] = mapped_column(
        String(40),
        ForeignKey("portfolio.portfolio_id"),
        nullable=True,
        index=True,
    )
    proposal_id: Mapped[Optional[str]] = mapped_column(
        String(30),
        ForeignKey("rebalance_proposal.proposal_id"),
        nullable=True,
        index=True,
    )
    workflow_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("workflow_runs.id"),
        nullable=True,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    portfolio: Mapped[Optional["Portfolio"]] = relationship("Portfolio")
    proposal: Mapped[Optional["RebalanceProposal"]] = relationship("RebalanceProposal")
    workflow_run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun")

    def __repr__(self) -> str:
        return (
            f"<AuditEvent(event_id='{self.event_id}', action='{self.action}', "
            f"actor_id='{self.actor_id}', entity='{self.entity_type}:{self.entity_id}', "
            f"timestamp='{self.timestamp}')>"
        )

