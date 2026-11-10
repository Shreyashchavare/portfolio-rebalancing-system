"""Portfolio SQLAlchemy entity."""

from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.investor_profile import InvestorProfile


class PortfolioStatus(str, enum.Enum):
    """Portfolio operational status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Portfolio(Base):
    """Portfolio entity belonging to an investor."""

    __tablename__ = "portfolio"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="check_portfolio_status_valid",
        ),
    )

    portfolio_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investor_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("investor_profile.investor_id"),
        nullable=False,
    )
    portfolio_name: Mapped[str] = mapped_column(String, nullable=False)
    base_currency: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PortfolioStatus] = mapped_column(
        Enum(
            PortfolioStatus,
            name="portfolio_status_enum",
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

    # Relationships
    investor: Mapped["InvestorProfile"] = relationship(
        "InvestorProfile",
        back_populates="portfolios",
    )

