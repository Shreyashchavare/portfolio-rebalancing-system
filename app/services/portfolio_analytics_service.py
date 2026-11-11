"""Core Portfolio Analytics Service.

Provides deterministic portfolio valuation, asset-class weight calculation,
missing/stale price diagnostics, and target allocation drift analysis.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Mapping, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.constraint import Constraint
from app.models.holding import Holding
from app.models.instrument import Instrument
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio
from app.models.target_allocation import TargetAllocation
from app.schemas.portfolio_analytics import (
    AssetClassAllocation,
    AssetClassDrift,
    PortfolioDriftResult,
    PortfolioValuationResult,
    PositionValuation,
    RebalanceTriggerEvaluation,
)
from synthetic_data.calculations import (
    calculate_allocation_drift,
    calculate_asset_class_weights,
    calculate_portfolio_market_value,
    calculate_position_market_value,
)


class PortfolioNotFoundError(Exception):
    """Raised when a portfolio ID cannot be found in the database."""

    def __init__(self, portfolio_id: str) -> None:
        super().__init__(f"Portfolio not found: {portfolio_id}")
        self.portfolio_id = portfolio_id


class MissingPriceError(Exception):
    """Raised when an instrument lacks a market price on or before the as-of date."""

    def __init__(self, instrument_id: str, as_of_date: date) -> None:
        super().__init__(
            f"Missing market price for instrument {instrument_id} on or before {as_of_date}"
        )
        self.instrument_id = instrument_id
        self.as_of_date = as_of_date


class PortfolioAnalyticsService:
    """Production service for portfolio valuation, allocation analysis, and drift metrics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_portfolio_or_raise(self, portfolio_id: str) -> Portfolio:
        """Fetch portfolio entity or raise PortfolioNotFoundError."""
        portfolio = (
            self.session.query(Portfolio)
            .filter(Portfolio.portfolio_id == portfolio_id)
            .first()
        )
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)
        return portfolio

    def _get_effective_targets(
        self, portfolio_id: str, as_of_date: date
    ) -> dict[str, Decimal]:
        """Fetch effective target allocations for a portfolio as of a given date."""
        targets = (
            self.session.query(TargetAllocation)
            .filter(
                TargetAllocation.portfolio_id == portfolio_id,
                TargetAllocation.effective_from <= as_of_date,
                (
                    TargetAllocation.effective_to.is_(None)
                    | (TargetAllocation.effective_to >= as_of_date)
                ),
            )
            .all()
        )
        return {t.asset_class: t.target_weight for t in targets}

    def get_portfolio_valuation(
        self, portfolio_id: str, as_of_date: date
    ) -> PortfolioValuationResult:
        """Calculate aggregate portfolio market value, positions, and asset-class weights."""
        self._get_portfolio_or_raise(portfolio_id)

        # 1. Retrieve latest available holdings snapshot on or before as_of_date
        latest_holding_date = (
            self.session.query(func.max(Holding.as_of_date))
            .filter(
                Holding.portfolio_id == portfolio_id,
                Holding.as_of_date <= as_of_date,
            )
            .scalar()
        )

        if not latest_holding_date:
            holdings = []
        else:
            holdings = (
                self.session.query(Holding)
                .filter(
                    Holding.portfolio_id == portfolio_id,
                    Holding.as_of_date == latest_holding_date,
                )
                .all()
            )

        positions: list[PositionValuation] = []
        class_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))

        # 2. Value each holding position
        for h in holdings:
            inst = (
                h.instrument
                or self.session.query(Instrument)
                .filter(Instrument.instrument_id == h.instrument_id)
                .first()
            )
            asset_class = inst.asset_class if inst else "UNKNOWN"
            symbol = inst.symbol if inst else None
            instrument_name = inst.instrument_name if inst else None

            # Resolve latest market price on or before as_of_date
            latest_price_rec = (
                self.session.query(MarketPrice)
                .filter(
                    MarketPrice.instrument_id == h.instrument_id,
                    MarketPrice.price_date <= as_of_date,
                )
                .order_by(MarketPrice.price_date.desc())
                .first()
            )

            if not latest_price_rec:
                raise MissingPriceError(h.instrument_id, as_of_date)

            unit_price = latest_price_rec.price
            market_val = calculate_position_market_value(h.quantity, unit_price)

            price_age_days = (as_of_date - latest_price_rec.price_date).days
            if price_age_days == 0:
                is_stale = False
                diagnostic = None
            else:
                # With no explicit staleness threshold/calendar policy configured,
                # classify staleness as unknown (None) while exposing price age and diagnostic.
                is_stale = None
                diagnostic = (
                    f"Price as of {latest_price_rec.price_date} is {price_age_days} day(s) old "
                    f"relative to as-of date {as_of_date}"
                )

            positions.append(
                PositionValuation(
                    holding_id=h.holding_id,
                    portfolio_id=portfolio_id,
                    instrument_id=h.instrument_id,
                    symbol=symbol,
                    instrument_name=instrument_name,
                    asset_class=asset_class,
                    quantity=h.quantity,
                    unit_price=unit_price,
                    market_value=market_val,
                    price_date=latest_price_rec.price_date,
                    price_age_days=price_age_days,
                    is_stale=is_stale,
                    diagnostic=diagnostic,
                )
            )
            class_values[asset_class] += market_val

        # 3. Calculate total portfolio market value
        total_market_val = sum(p.market_value for p in positions) if positions else Decimal("0.0000")
        total_market_val = total_market_val.quantize(Decimal("0.0001"))

        # 4. Calculate asset class weights
        if not positions or total_market_val == Decimal("0.0000"):
            asset_classes = []
        else:
            # Include asset classes from target allocations even if no holdings currently exist
            targets = self._get_effective_targets(portfolio_id, as_of_date)
            all_classes = sorted(set(class_values.keys()).union(set(targets.keys())))

            weights: dict[str, Decimal] = {}
            for ac in all_classes:
                val = class_values[ac]
                w = ((val / total_market_val) * Decimal("100.0000")).quantize(Decimal("0.0001"))
                weights[ac] = w

            # Reconcile rounding residual against the largest allocation weight
            weight_sum = sum(weights.values())
            drift = Decimal("100.0000") - weight_sum
            if drift != Decimal("0.0000") and weights:
                largest_ac = max(weights.keys(), key=lambda k: weights[k])
                weights[largest_ac] = (weights[largest_ac] + drift).quantize(Decimal("0.0001"))

            asset_classes = [
                AssetClassAllocation(
                    asset_class=ac,
                    market_value=class_values[ac].quantize(Decimal("0.0001")),
                    current_weight=weights[ac],
                )
                for ac in all_classes
            ]

        return PortfolioValuationResult(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            total_market_value=total_market_val,
            positions=positions,
            asset_classes=asset_classes,
        )

    def get_portfolio_drift(
        self, portfolio_id: str, as_of_date: date
    ) -> PortfolioDriftResult:
        """Calculate allocation drift (actual vs target) across all relevant asset classes."""
        valuation = self.get_portfolio_valuation(portfolio_id, as_of_date)
        targets = self._get_effective_targets(portfolio_id, as_of_date)

        actual_weights = {a.asset_class: a.current_weight for a in valuation.asset_classes}
        actual_values = {a.asset_class: a.market_value for a in valuation.asset_classes}

        all_classes = sorted(set(actual_weights.keys()).union(set(targets.keys())))

        drifts: list[AssetClassDrift] = []
        for ac in all_classes:
            curr_w = actual_weights.get(ac, Decimal("0.0000"))
            tgt_w = targets.get(ac, Decimal("0.0000"))
            curr_val = actual_values.get(ac, Decimal("0.0000"))
            tgt_val = (
                (tgt_w / Decimal("100.0000")) * valuation.total_market_value
            ).quantize(Decimal("0.0001"))

            pct_drift = (curr_w - tgt_w).quantize(Decimal("0.0001"))
            monetary_drift = (
                (pct_drift / Decimal("100.0000")) * valuation.total_market_value
            ).quantize(Decimal("0.0001"))

            signal = (
                "SELL"
                if pct_drift > Decimal("0.0000")
                else ("BUY" if pct_drift < Decimal("0.0000") else "HOLD")
            )

            drifts.append(
                AssetClassDrift(
                    asset_class=ac,
                    current_market_value=curr_val,
                    target_market_value=tgt_val,
                    current_weight=curr_w,
                    target_weight=tgt_w,
                    percentage_drift=pct_drift,
                    monetary_drift=monetary_drift,
                    action_signal=signal,
                )
            )

        # Reconcile minor monetary drift rounding residue if targets and weights sum to 100%
        if drifts and valuation.total_market_value > Decimal("0.0000"):
            total_pct_drift = sum(d.percentage_drift for d in drifts)
            if total_pct_drift == Decimal("0.0000"):
                total_monetary_drift = sum(d.monetary_drift for d in drifts)
                if total_monetary_drift != Decimal("0.0000"):
                    # Reconcile residual against the largest absolute monetary drift
                    largest_drift_item = max(drifts, key=lambda d: abs(d.monetary_drift))
                    largest_drift_item.monetary_drift = (
                        largest_drift_item.monetary_drift - total_monetary_drift
                    ).quantize(Decimal("0.0001"))

        rebalance_trigger = self.evaluate_rebalance_trigger(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            valuation=valuation,
        )

        return PortfolioDriftResult(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            total_market_value=valuation.total_market_value,
            drifts=drifts,
            rebalance_trigger=rebalance_trigger,
        )

    def evaluate_rebalance_trigger(
        self,
        portfolio_id: str,
        as_of_date: date,
        valuation: PortfolioValuationResult,
    ) -> RebalanceTriggerEvaluation:
        """Deterministic rebalance trigger evaluation against active configured constraints."""
        # Query active portfolio-scoped constraints effective on as_of_date
        constraints = (
            self.session.query(Constraint)
            .filter(
                Constraint.scope_type == "PORTFOLIO",
                Constraint.scope_reference_id == portfolio_id,
                Constraint.is_active.is_(True),
                Constraint.effective_from <= as_of_date,
                (
                    Constraint.effective_to.is_(None)
                    | (Constraint.effective_to >= as_of_date)
                ),
            )
            .all()
        )

        weight_constraints = [
            c
            for c in constraints
            if c.constraint_type in ("MAX_POSITION_WEIGHT", "MIN_POSITION_WEIGHT")
            and c.threshold_value is not None
        ]

        if not weight_constraints:
            return RebalanceTriggerEvaluation(
                status="NOT_CONFIGURED",
                rebalance_required=None,
                triggered_asset_classes=[],
                triggered_positions=[],
                policy_description="No explicit rebalance threshold policy configured for portfolio.",
            )

        triggered_classes: set[str] = set()
        triggered_positions: set[str] = set()
        breach_descriptions: list[str] = []

        # Evaluate instrument-level position weights for PORTFOLIO-scoped position weight constraints
        if valuation.total_market_value > Decimal("0.0000"):
            for p in valuation.positions:
                pos_weight = (
                    (p.market_value / valuation.total_market_value) * Decimal("100.0000")
                ).quantize(Decimal("0.0001"))
                pos_id = p.symbol or p.instrument_id

                for c in weight_constraints:
                    if c.constraint_type == "MAX_POSITION_WEIGHT":
                        if pos_weight > c.threshold_value:
                            triggered_positions.add(pos_id)
                            triggered_classes.add(p.asset_class)
                            breach_descriptions.append(
                                f"Position {pos_id} ({p.asset_class}) weight {pos_weight}% "
                                f"exceeds max threshold {c.threshold_value}%"
                            )
                    elif c.constraint_type == "MIN_POSITION_WEIGHT":
                        if p.quantity > Decimal("0.0000") and pos_weight < c.threshold_value:
                            triggered_positions.add(pos_id)
                            triggered_classes.add(p.asset_class)
                            breach_descriptions.append(
                                f"Position {pos_id} ({p.asset_class}) weight {pos_weight}% "
                                f"is below min threshold {c.threshold_value}%"
                            )

        if triggered_positions:
            return RebalanceTriggerEvaluation(
                status="TRIGGERED",
                rebalance_required=True,
                triggered_asset_classes=sorted(list(triggered_classes)),
                triggered_positions=sorted(list(triggered_positions)),
                policy_description=f"Rebalance triggered by policy breaches: {'; '.join(breach_descriptions)}",
            )
        else:
            return RebalanceTriggerEvaluation(
                status="NOT_TRIGGERED",
                rebalance_required=False,
                triggered_asset_classes=[],
                triggered_positions=[],
                policy_description="All evaluated allocation constraints are satisfied.",
            )


