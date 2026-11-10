"""Instrument SQLAlchemy entity."""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Instrument(Base):
    """Financial instrument definition."""

    __tablename__ = "instrument"
    __table_args__ = (
        CheckConstraint(
            "lot_size > 0",
            name="check_lot_size_positive",
        ),
    )

    instrument_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    instrument_name: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

