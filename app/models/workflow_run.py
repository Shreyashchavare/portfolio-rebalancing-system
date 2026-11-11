"""WorkflowRun SQLAlchemy model for orchestrating rebalancing workflows."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.rebalance_proposal import RebalanceProposal


class WorkflowRun(Base):
    """Workflow execution run entity coordinating analytics, rebalancing, and policy RAG."""

    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "request_key",
            name="uq_workflow_runs_portfolio_request_key",
        ),
        CheckConstraint(
            "status IN ("
            "'RECEIVED', 'VALIDATING', 'ANALYZING', 'GENERATING_PROPOSAL', "
            "'RETRIEVING_POLICIES', 'GENERATING_EXPLANATION', 'PENDING_HUMAN_REVIEW', "
            "'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED', 'REQUIRES_ATTENTION'"
            ")",
            name="check_workflow_run_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("portfolio.portfolio_id"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[Optional[str]] = mapped_column(
        String(30),
        ForeignKey("rebalance_proposal.proposal_id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    request_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio")
    proposal: Mapped[Optional["RebalanceProposal"]] = relationship("RebalanceProposal")

    @property
    def workflow_id(self) -> str:
        """Alias property for workflow run primary key identifier."""
        return self.id

    def __repr__(self) -> str:
        return (
            f"<WorkflowRun(id='{self.id}', portfolio_id='{self.portfolio_id}', "
            f"status='{self.status}', proposal_id='{self.proposal_id}')>"
        )

