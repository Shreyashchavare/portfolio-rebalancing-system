from fastapi import FastAPI

app = FastAPI(
    title="Portfolio Rebalancing System",
    description="Policy-Constrained Portfolio Rebalancing Recommendation System",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint to verify application status."""
    return {"status": "healthy"}
