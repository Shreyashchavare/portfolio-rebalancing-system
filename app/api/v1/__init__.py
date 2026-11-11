"""Version 1 API routers."""

from app.api.v1.analytics import router as analytics_router
from app.api.v1.approvals import router as approvals_router
from app.api.v1.policies import router as policies_router
from app.api.v1.rebalancing import router as rebalancing_router
from app.api.v1.workflows import router as workflows_router

__all__ = [
    "analytics_router",
    "approvals_router",
    "policies_router",
    "rebalancing_router",
    "workflows_router",
]
