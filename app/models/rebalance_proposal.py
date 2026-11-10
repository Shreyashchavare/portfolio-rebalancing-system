"""RebalanceProposal SQLAlchemy entity."""

from datetime import datetime, timezone
from decimal import Decimal
import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.trade import Trade


class ProposalStatus(str, enum.Enum):
    """Lifecycle statuses for a rebalancing proposal."""

    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewDecision(str, enum.Enum):
    """Review decision states for human-in-the-loop governance."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RebalanceProposal(Base):
    """Rebalancing proposal containing proposed portfolio adjustments and review status."""

    __tablename__ = "rebalance_proposal"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED')",
            name="check_rebalance_proposal_status_valid",
        ),
        CheckConstraint(
            "review_decision IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="check_rebalance_proposal_review_decision_valid",
        ),
        CheckConstraint(
            "pre_trade_portfolio_value IS NULL OR pre_trade_portfolio_value >= 0",
            name="check_rebalance_proposal_pre_value_nonnegative",
        ),
        CheckConstraint(
            "post_trade_portfolio_value IS NULL OR post_trade_portfolio_value >= 0",
            name="check_rebalance_proposal_post_value_nonnegative",
        ),
    )

    proposal_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("portfolio.portfolio_id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    review_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    pre_trade_portfolio_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    post_trade_portfolio_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="proposals",
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade",
        back_populates="proposal",
    )

