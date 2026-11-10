"""FeeSchedule SQLAlchemy entity."""

from datetime import date
from decimal import Decimal
import enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Numeric,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TradeSide(str, enum.Enum):
    """Trading side classification."""

    BUY = "BUY"
    SELL = "SELL"


class FeeSchedule(Base):
    """Fee schedule defining trading fees across notional value tiers."""

    __tablename__ = "fee_schedule"
    __table_args__ = (
        CheckConstraint(
            "min_trade_value >= 0 AND (max_trade_value IS NULL OR max_trade_value >= min_trade_value)",
            name="check_fee_schedule_trade_value_range",
        ),
        CheckConstraint(
            "fee_rate_bps >= 0 AND fixed_fee >= 0 AND minimum_fee >= 0",
            name="check_fee_schedule_fees_nonnegative",
        ),
        CheckConstraint(
            "maximum_fee IS NULL OR maximum_fee >= minimum_fee",
            name="check_fee_schedule_maximum_fee",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="check_fee_schedule_effective_dates",
        ),
        CheckConstraint(
            "trade_side IN ('BUY', 'SELL')",
            name="check_fee_schedule_trade_side_valid",
        ),
        UniqueConstraint(
            "asset_class",
            "trade_side",
            "min_trade_value",
            "effective_from",
            name="uq_fee_schedule_tier",
        ),
    )

    fee_schedule_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    trade_side: Mapped[str] = mapped_column(String(4), nullable=False)
    min_trade_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    max_trade_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    fee_rate_bps: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    fixed_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    minimum_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    maximum_fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

