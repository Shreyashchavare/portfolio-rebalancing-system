"""InvestorProfile SQLAlchemy entity."""

from datetime import datetime, timezone
import enum

from sqlalchemy import CheckConstraint, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RiskCategory(str, enum.Enum):
    """Investor risk category."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class InvestorProfile(Base):
    """Investor profile entity defining risk tolerance and identification."""

    __tablename__ = "investor_profile"
    __table_args__ = (
        CheckConstraint(
            "risk_category IN ('LOW', 'MODERATE', 'HIGH')",
            name="check_risk_category_valid",
        ),
    )

    investor_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    risk_category: Mapped[RiskCategory] = mapped_column(
        Enum(
            RiskCategory,
            name="risk_category_enum",
            values_callable=lambda obj: [e.value for e in obj],
            validate_strings=True,
            native_enum=False,
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
