"""MarketPrice SQLAlchemy entity."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

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
    from app.models.instrument import Instrument


class MarketPrice(Base):
    """Market price snapshot for a financial instrument on a given date."""

    __tablename__ = "market_price"
    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="check_market_price_positive",
        ),
        UniqueConstraint(
            "instrument_id",
            "price_date",
            name="uq_market_price_instrument_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(),
        primary_key=True,
        autoincrement=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instrument.instrument_id"),
        nullable=False,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)

    # Relationship to Instrument
    instrument: Mapped["Instrument"] = relationship("Instrument")
