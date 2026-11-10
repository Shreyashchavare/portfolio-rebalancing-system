"""ConstraintInstrument association entity."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.constraint import Constraint
    from app.models.instrument import Instrument


class ConstraintInstrument(Base):
    """Bridge table for many-to-many associations between Constraint and Instrument."""

    __tablename__ = "constraint_instrument"

    constraint_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("constraint.constraint_id"),
        primary_key=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("instrument.instrument_id"),
        primary_key=True,
    )

    # Direct relationships with overlap specification for many-to-many mapping
    constraint: Mapped["Constraint"] = relationship(
        "Constraint", overlaps="instruments,constraints"
    )
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", overlaps="instruments,constraints"
    )
