"""Backward-compatible facade for RebalancingService.

Preserves existing import paths while modular domain logic lives in
app.services.rebalancing.
"""

from app.services.rebalancing.constraint_evaluator import ConstraintEvaluator
from app.services.rebalancing.rebalancing_service import (
    ConstraintViolationError,
    RebalancingService,
)
from app.services.rebalancing.trade_generator import TradeGenerator
from app.services.rebalancing.trade_simulator import TradeSimulator

__all__ = [
    "ConstraintEvaluator",
    "ConstraintViolationError",
    "RebalancingService",
    "TradeGenerator",
    "TradeSimulator",
]
