"""Version 1 API routers."""

from app.api.v1.analytics import router as analytics_router
from app.api.v1.policies import router as policies_router
from app.api.v1.rebalancing import router as rebalancing_router

__all__ = ["analytics_router", "policies_router", "rebalancing_router"]
