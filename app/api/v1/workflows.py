"""REST API endpoints for workflow execution initiation, querying, and tracking."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_reviewer
from app.database.session import get_db
from app.schemas.approval import ReviewerContext
from app.schemas.orchestration import (
    IdempotencyConflictError,
    WorkflowExecutionError,
    WorkflowRequest,
    WorkflowResponse,
)
from app.services.orchestration.workflow_service import WorkflowService
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow Orchestration"])


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate or resume an orchestrated rebalancing workflow",
    description="Trigger complete deterministic rebalance workflow with grounded explanation, policy retrieval, and human review gating.",
)
def initiate_workflow(
    request: WorkflowRequest,
    reviewer: ReviewerContext = Depends(get_current_reviewer),
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    """Initiate or resume an orchestrated rebalancing workflow run with authenticated reviewer identity."""
    service = WorkflowService(db)
    try:
        return service.run_workflow(request)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PortfolioNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except WorkflowExecutionError as exc:
        cause = getattr(exc, "__cause__", None)
        if isinstance(cause, PortfolioNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(cause),
            ) from exc
        if isinstance(cause, MissingPriceError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(cause),
            ) from exc
        logger.warning("Workflow execution failed for portfolio %s: %s", request.portfolio_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in workflow execution for %s: %s", request.portfolio_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during workflow execution.",
        ) from exc


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve workflow execution status and results",
    description="Query an orchestrated workflow run, including its proposal, grounded explanation, and audit status.",
)
def get_workflow_by_id(
    workflow_id: str,
    db: Session = Depends(get_db),
) -> WorkflowResponse:
    """Retrieve details of an orchestrated workflow execution run."""
    service = WorkflowService(db)
    result = service.get_workflow(workflow_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{workflow_id}' was not found.",
        )
    return result
