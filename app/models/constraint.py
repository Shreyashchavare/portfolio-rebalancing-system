"""Constraint SQLAlchemy entity and validation helpers."""

from datetime import date
from decimal import Decimal
import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Numeric,
    String,
    Text,
    true,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.instrument import Instrument


class ScopeType(str, enum.Enum):
    """Scope target classification for policy constraints."""

    PORTFOLIO = "PORTFOLIO"
    ASSET_CLASS = "ASSET_CLASS"
    INSTRUMENT = "INSTRUMENT"


class ConstraintSeverity(str, enum.Enum):
    """Constraint enforcement severity."""

    HARD = "HARD"
    SOFT = "SOFT"


class ConstraintType(str, enum.Enum):
    """Supported portfolio constraint types."""

    MAX_POSITION_WEIGHT = "MAX_POSITION_WEIGHT"
    MIN_POSITION_WEIGHT = "MIN_POSITION_WEIGHT"
    MIN_TRADE_VALUE = "MIN_TRADE_VALUE"
    MAX_TRADE_VALUE = "MAX_TRADE_VALUE"
    MIN_TRADE_QUANTITY = "MIN_TRADE_QUANTITY"
    MAX_TRADE_QUANTITY = "MAX_TRADE_QUANTITY"
    EXCLUDED_INSTRUMENT = "EXCLUDED_INSTRUMENT"
    LIQUIDITY_LIMIT = "LIQUIDITY_LIMIT"


class Constraint(Base):
    """Policy constraint governing portfolio allocation, trading rules, and risk limits."""

    __tablename__ = "constraint"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('PORTFOLIO', 'ASSET_CLASS', 'INSTRUMENT')",
            name="check_constraint_scope_type_valid",
        ),
        CheckConstraint(
            "severity IN ('HARD', 'SOFT')",
            name="check_constraint_severity_valid",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="check_constraint_effective_dates",
        ),
        CheckConstraint(
            "threshold_value IS NULL OR threshold_value >= 0",
            name="check_constraint_threshold_nonnegative",
        ),
        CheckConstraint(
            "constraint_type IN ("
            "'MAX_POSITION_WEIGHT', 'MIN_POSITION_WEIGHT', 'MIN_TRADE_VALUE', "
            "'MAX_TRADE_VALUE', 'MIN_TRADE_QUANTITY', 'MAX_TRADE_QUANTITY', "
            "'EXCLUDED_INSTRUMENT', 'LIQUIDITY_LIMIT'"
            ")",
            name="check_constraint_type_valid",
        ),
    )

    constraint_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    constraint_name: Mapped[str] = mapped_column(String(100), nullable=False)
    constraint_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_reference_id: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    threshold_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Many-to-many relationship with Instrument through bridge table
    instruments: Mapped[list["Instrument"]] = relationship(
        "Instrument",
        secondary="constraint_instrument",
        back_populates="constraints",
    )


def validate_scope_reference(
    scope_type: ScopeType | str,
    scope_reference_id: str,
    session: Session,
) -> bool:
    """Validate that polymorphic scope_reference_id matches an existing entity according to scope_type.

    - PORTFOLIO: verifies that a Portfolio exists with portfolio_id == scope_reference_id.
    - INSTRUMENT: verifies that an Instrument exists with instrument_id == scope_reference_id.
    - ASSET_CLASS: verifies that scope_reference_id is a non-empty string identifier.
    """
    if not scope_reference_id:
        return False

    raw_scope = scope_type.value if hasattr(scope_type, "value") else str(scope_type)

    if raw_scope == ScopeType.PORTFOLIO.value:
        from app.models.portfolio import Portfolio

        return session.get(Portfolio, scope_reference_id) is not None
    elif raw_scope == ScopeType.INSTRUMENT.value:
        from app.models.instrument import Instrument

        return session.get(Instrument, scope_reference_id) is not None
    elif raw_scope == ScopeType.ASSET_CLASS.value:
        return bool(scope_reference_id.strip())

    return False

