"""Deterministic in-memory simulation of post-trade portfolio holdings and allocations.

Simulates applying proposed BUY and SELL trades to a portfolio's positions,
enforcing cash solvency, computing post-trade position market values, asset class
weights, and residual drift against target allocations.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.schemas.rebalancing import (
    PostTradeSimulationResult,
    ProposedTrade,
    SimulatedAllocation,
    SimulatedPosition,
)
from app.services.portfolio_analytics_service import PortfolioAnalyticsService


class TradeSimulator:
    """Simulates post-trade holding states, cash balances, and allocation weights without modifying database records."""

    def __init__(
        self,
        session: Session,
        analytics_service: Optional[PortfolioAnalyticsService] = None,
    ) -> None:
        self.session = session
        self.analytics_service = analytics_service or PortfolioAnalyticsService(session)

    def simulate_post_trade_state(
        self,
        portfolio_id: str,
        as_of_date: date,
        proposed_trades: list[ProposedTrade],
    ) -> PostTradeSimulationResult:
        """Execute deterministic, in-memory simulation of proposed trades on portfolio holdings."""
        valuation = self.analytics_service.get_portfolio_valuation(portfolio_id, as_of_date)
        targets = self.analytics_service._get_effective_targets(portfolio_id, as_of_date)

        # Validate trade inputs
        for t in proposed_trades:
            if t.quantity <= Decimal("0.0000"):
                raise ValueError(f"Invalid trade input: non-positive quantity {t.quantity}")
            if t.unit_price <= Decimal("0.0000"):
                raise ValueError(f"Invalid trade input: non-positive unit price {t.unit_price}")

        # In-memory map of existing non-cash positions
        sim_pos_dict: dict[str, dict] = {}
        for p in valuation.positions:
            if p.asset_class != "CASH":
                sim_pos_dict[p.instrument_id] = {
                    "instrument_id": p.instrument_id,
                    "symbol": p.symbol,
                    "instrument_name": p.instrument_name,
                    "asset_class": p.asset_class,
                    "pre_trade_quantity": p.quantity,
                    "post_trade_quantity": p.quantity,
                    "unit_price": p.unit_price,
                }

        # Track executable trade financials
        total_executable_sell_notional = Decimal("0.0000")
        total_executable_sell_fees = Decimal("0.0000")
        total_executable_buy_notional = Decimal("0.0000")
        total_executable_buy_fees = Decimal("0.0000")

        # 1. Apply executable SELL trades
        for t in proposed_trades:
            if t.status == "PROPOSED" and t.trade_side == "SELL":
                if t.instrument_id not in sim_pos_dict:
                    raise ValueError(f"Invalid trade input: cannot sell unheld instrument {t.instrument_id}")
                current_qty = sim_pos_dict[t.instrument_id]["post_trade_quantity"]
                if t.quantity > current_qty:
                    raise ValueError(
                        f"Invalid trade input: sell quantity {t.quantity} exceeds held quantity {current_qty} for {t.instrument_id}"
                    )
                sim_pos_dict[t.instrument_id]["post_trade_quantity"] = current_qty - t.quantity
                total_executable_sell_notional += t.trade_value
                total_executable_sell_fees += t.fee_amount

        # 2. Apply executable BUY trades
        for t in proposed_trades:
            if t.status == "PROPOSED" and t.trade_side == "BUY":
                if t.instrument_id in sim_pos_dict:
                    sim_pos_dict[t.instrument_id]["post_trade_quantity"] += t.quantity
                else:
                    sim_pos_dict[t.instrument_id] = {
                        "instrument_id": t.instrument_id,
                        "symbol": t.symbol,
                        "instrument_name": t.instrument_name,
                        "asset_class": t.asset_class,
                        "pre_trade_quantity": Decimal("0.0000"),
                        "post_trade_quantity": t.quantity,
                        "unit_price": t.unit_price,
                    }
                total_executable_buy_notional += t.trade_value
                total_executable_buy_fees += t.fee_amount

        total_executable_fees = (total_executable_sell_fees + total_executable_buy_fees).quantize(Decimal("0.0001"))

        # Starting cash
        pre_trade_cash = sum(
            (p.market_value for p in valuation.positions if p.asset_class == "CASH"),
            Decimal("0.0000"),
        )
        post_trade_cash = (
            pre_trade_cash + total_executable_sell_notional - total_executable_sell_fees
            - total_executable_buy_notional - total_executable_buy_fees
        ).quantize(Decimal("0.0001"))

        if post_trade_cash < Decimal("0.0000"):
            raise ValueError(f"Simulated cash cannot become negative: {post_trade_cash}")

        pre_trade_total = valuation.total_market_value
        post_trade_total = (pre_trade_total - total_executable_fees).quantize(Decimal("0.0001"))

        # Build simulated positions
        simulated_positions: list[SimulatedPosition] = []
        for inst_id, d in sorted(sim_pos_dict.items(), key=lambda item: item[0]):
            post_qty = d["post_trade_quantity"].quantize(Decimal("0.0001"))
            mkt_val = (post_qty * d["unit_price"]).quantize(Decimal("0.0001"))
            weight = (
                ((mkt_val / post_trade_total) * Decimal("100.0000")).quantize(Decimal("0.0001"))
                if post_trade_total > Decimal("0.0000")
                else Decimal("0.0000")
            )
            simulated_positions.append(
                SimulatedPosition(
                    instrument_id=inst_id,
                    symbol=d["symbol"],
                    instrument_name=d["instrument_name"],
                    asset_class=d["asset_class"],
                    pre_trade_quantity=d["pre_trade_quantity"],
                    post_trade_quantity=post_qty,
                    unit_price=d["unit_price"],
                    post_trade_market_value=mkt_val,
                    post_trade_weight=weight,
                )
            )

        # Asset class allocations & residual drift
        all_classes = sorted(
            set(targets.keys())
            .union(set(p.asset_class for p in simulated_positions))
            .union({"CASH"})
        )
        simulated_allocations: list[SimulatedAllocation] = []
        residual_drifts: dict[str, Decimal] = {}

        for ac in all_classes:
            if ac == "CASH":
                ac_val = post_trade_cash
            else:
                ac_val = sum(
                    p.post_trade_market_value
                    for p in simulated_positions
                    if p.asset_class == ac
                )
            ac_weight = (
                ((ac_val / post_trade_total) * Decimal("100.0000")).quantize(Decimal("0.0001"))
                if post_trade_total > Decimal("0.0000")
                else Decimal("0.0000")
            )
            target_w = targets.get(ac, Decimal("0.0000"))
            drift = (ac_weight - target_w).quantize(Decimal("0.0001"))
            residual_drifts[ac] = drift
            simulated_allocations.append(
                SimulatedAllocation(
                    asset_class=ac,
                    post_trade_market_value=ac_val,
                    post_trade_weight=ac_weight,
                    target_weight=target_w,
                    post_trade_drift=drift,
                )
            )

        return PostTradeSimulationResult(
            pre_trade_portfolio_value=pre_trade_total,
            post_trade_portfolio_value=post_trade_total,
            pre_trade_cash=pre_trade_cash,
            post_trade_cash=post_trade_cash,
            total_executable_fees=total_executable_fees,
            positions=simulated_positions,
            asset_classes=simulated_allocations,
            residual_drifts=residual_drifts,
        )

