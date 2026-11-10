"""Holding SQLAlchemy entity."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.instrument import Instrument
    from app.models.portfolio import Portfolio


class Holding(Base):
    """Holding entity representing an asset position in a portfolio on a specific date."""

    __tablename__ = "holding"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="check_holding_quantity_non_negative",
        ),
        UniqueConstraint(
            "portfolio_id",
            "instrument_id",
            "as_of_date",
            name="uq_holding_portfolio_instrument_date",
        ),
    )

    holding_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("portfolio.portfolio_id"),
        nullable=False,
    )
    instrument_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instrument.instrument_id"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships to parent entities
    portfolio: Mapped["Portfolio"] = relationship("Portfolio")
    instrument: Mapped["Instrument"] = relationship("Instrument")

