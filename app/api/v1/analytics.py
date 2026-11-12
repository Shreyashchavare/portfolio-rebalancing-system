"""Portfolio Analytics API endpoints."""

from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.portfolio import Portfolio
from app.schemas.portfolio_analytics import (
    PortfolioDriftResult,
    PortfolioListItem,
    PortfolioValuationResult,
)
from app.services.portfolio_analytics_service import (
    InvalidTargetAllocationError,
    MissingPriceError,
    PortfolioAnalyticsService,
    PortfolioNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portfolios", tags=["Portfolio Analytics"])


@router.get(
    "",
    response_model=list[PortfolioListItem],
    status_code=status.HTTP_200_OK,
    summary="List all portfolios",
    description="Retrieve all available portfolios for analytics, drift surveillance, and rebalancing.",
)
def list_portfolios(
    db: Session = Depends(get_db),
) -> list[PortfolioListItem]:
    """Retrieve all available portfolios."""
    portfolios = db.query(Portfolio).order_by(Portfolio.portfolio_id).all()
    return [
        PortfolioListItem(
            portfolio_id=p.portfolio_id,
            investor_id=p.investor_id,
            portfolio_name=p.portfolio_name,
            base_currency=p.base_currency,
            status=p.status.value if hasattr(p.status, "value") else str(p.status),
        )
        for p in portfolios
    ]


@router.get(
    "/{portfolio_id}/valuation",
    response_model=PortfolioValuationResult,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio valuation",
    description="Calculate aggregate portfolio market value, positions, and asset-class weights as of a given date.",
)
def get_portfolio_valuation(
    portfolio_id: str,
    as_of_date: Optional[date] = Query(
        default=None,
        description="Valuation as-of date (YYYY-MM-DD). Defaults to today if omitted.",
    ),
    db: Session = Depends(get_db),
) -> PortfolioValuationResult:
    """Return portfolio valuation and position breakdowns."""
    target_date = as_of_date or date.today()
    service = PortfolioAnalyticsService(db)
    try:
        return service.get_portfolio_valuation(portfolio_id=portfolio_id, as_of_date=target_date)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MissingPriceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during portfolio valuation for %s: %s", portfolio_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        ) from exc


@router.get(
    "/{portfolio_id}/drift",
    response_model=PortfolioDriftResult,
    status_code=status.HTTP_200_OK,
    summary="Get portfolio drift analysis",
    description="Calculate asset class allocation drift against target allocations and evaluate rebalance triggers.",
)
def get_portfolio_drift(
    portfolio_id: str,
    as_of_date: Optional[date] = Query(
        default=None,
        description="Drift evaluation as-of date (YYYY-MM-DD). Defaults to today if omitted.",
    ),
    db: Session = Depends(get_db),
) -> PortfolioDriftResult:
    """Return portfolio allocation drift and rebalance trigger status."""
    target_date = as_of_date or date.today()
    service = PortfolioAnalyticsService(db)
    try:
        return service.get_portfolio_drift(portfolio_id=portfolio_id, as_of_date=target_date)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (MissingPriceError, InvalidTargetAllocationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during portfolio drift analysis for %s: %s", portfolio_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        ) from exc

