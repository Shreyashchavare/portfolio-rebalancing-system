"""Portfolio Rebalancing API endpoints."""

from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.rebalancing import (
    CreateProposalRequest,
    RebalanceProposalResponse,
)
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioNotFoundError,
)
from app.services.rebalancing_service import (
    ConstraintViolationError,
    RebalancingService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portfolios", tags=["Portfolio Rebalancing"])


@router.post(
    "/{portfolio_id}/rebalance/proposals",
    response_model=RebalanceProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and persist a rebalancing proposal",
    description="Generate deterministic recommendations, run post-trade simulation, evaluate policy constraints, and persist a proposal.",
)
def create_rebalance_proposal(
    portfolio_id: str,
    as_of_date: Optional[date] = Query(
        default=None,
        description="Rebalancing as-of date (YYYY-MM-DD). Defaults to today or payload date if omitted.",
    ),
    payload: Optional[CreateProposalRequest] = None,
    db: Session = Depends(get_db),
) -> RebalanceProposalResponse:
    """Generate, validate, simulate, and persist a rebalancing proposal."""
    target_date = (
        (payload.as_of_date if payload and payload.as_of_date else None)
        or as_of_date
        or date.today()
    )
    service = RebalancingService(db)
    try:
        return service.create_and_persist_proposal(portfolio_id=portfolio_id, as_of_date=target_date)
    except PortfolioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MissingPriceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except (ConstraintViolationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error creating rebalance proposal for %s: %s", portfolio_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        ) from exc

