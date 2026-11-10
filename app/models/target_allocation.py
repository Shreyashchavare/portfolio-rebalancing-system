"""TargetAllocation SQLAlchemy entity."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class TargetAllocation(Base):
    """Target asset class allocation for a portfolio over an effective date range."""

    __tablename__ = "target_allocation"
    __table_args__ = (
        CheckConstraint(
            "target_weight >= 0 AND target_weight <= 100",
            name="check_target_allocation_weight_range",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="check_target_allocation_effective_dates",
        ),
        UniqueConstraint(
            "portfolio_id",
            "asset_class",
            "effective_from",
            name="uq_target_allocation_portfolio_asset_effective_from",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(),
        primary_key=True,
        autoincrement=True,
    )
    portfolio_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("portfolio.portfolio_id"),
        nullable=False,
    )
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationship to Portfolio
    portfolio: Mapped["Portfolio"] = relationship("Portfolio")

