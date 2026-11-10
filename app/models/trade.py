"""Trade SQLAlchemy entity."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.fee_schedule import FeeSchedule
    from app.models.instrument import Instrument
    from app.models.rebalance_proposal import RebalanceProposal


class TradeStatus(str, enum.Enum):
    """Trading execution and governance status."""

    PROPOSED = "PROPOSED"
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Trade(Base):
    """Proposed or approved trade within a rebalance proposal."""

    __tablename__ = "trade"
    __table_args__ = (
        CheckConstraint(
            "trade_side IN ('BUY', 'SELL')",
            name="check_trade_side_valid",
        ),
        CheckConstraint(
            "status IN ('PROPOSED', 'BLOCKED', 'APPROVED', 'REJECTED')",
            name="check_trade_status_valid",
        ),
        CheckConstraint(
            "quantity > 0",
            name="check_trade_quantity_positive",
        ),
        CheckConstraint(
            "unit_price > 0",
            name="check_trade_unit_price_positive",
        ),
        CheckConstraint(
            "trade_value > 0",
            name="check_trade_value_positive",
        ),
        CheckConstraint(
            "fee_amount >= 0",
            name="check_trade_fee_amount_nonnegative",
        ),
    )

    trade_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("rebalance_proposal.proposal_id"),
        nullable=False,
    )
    instrument_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instrument.instrument_id"),
        nullable=False,
    )
    fee_schedule_id: Mapped[Optional[str]] = mapped_column(
        String(20),
        ForeignKey("fee_schedule.fee_schedule_id"),
        nullable=True,
    )
    trade_side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    trade_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    proposal: Mapped["RebalanceProposal"] = relationship(
        "RebalanceProposal",
        back_populates="trades",
    )
    instrument: Mapped["Instrument"] = relationship(
        "Instrument",
        back_populates="trades",
    )
    fee_schedule: Mapped[Optional["FeeSchedule"]] = relationship(
        "FeeSchedule",
        back_populates="trades",
    )

