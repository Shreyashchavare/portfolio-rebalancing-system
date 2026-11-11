from fastapi import FastAPI

from app.api.v1.analytics import router as analytics_router
from app.api.v1.policies import router as policies_router
from app.api.v1.rebalancing import router as rebalancing_router

app = FastAPI(
    title="Portfolio Rebalancing System",
    description="Policy-Constrained Portfolio Rebalancing Recommendation System",
    version="0.1.0",
)

app.include_router(analytics_router)
app.include_router(policies_router)
app.include_router(rebalancing_router)


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint to verify application status."""
    return {"status": "healthy"}
