"""Deterministic Rebalancing Trade Generation Service.

Converts portfolio allocation drift into lot-sized BUY and SELL recommendations
governed by fee schedules, available cash, lot constraints, excluded instruments,
post-trade simulation, constraint gatekeeper evaluation, and transactional persistence.
"""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.constraint import Constraint
from app.models.fee_schedule import FeeSchedule
from app.models.instrument import Instrument
from app.models.market_price import MarketPrice
from app.models.portfolio import Portfolio
from app.models.rebalance_proposal import (
    ProposalStatus,
    RebalanceProposal,
    ReviewDecision,
)
from app.models.trade import Trade, TradeStatus
from app.schemas.portfolio_analytics import PositionValuation
from app.schemas.rebalancing import (
    ConstraintFinding,
    PostTradeSimulationResult,
    ProposedTrade,
    RebalanceProposalResponse,
    RebalanceRecommendationResult,
    SimulatedAllocation,
    SimulatedPosition,
    TradeResponse,
)
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioAnalyticsService,
    PortfolioNotFoundError,
)
from synthetic_data.calculations import (
    calculate_trade_fee,
    calculate_trade_notional,
    match_fee_tier,
)


class ConstraintViolationError(ValueError):
    """Raised when a hard policy constraint is violated during proposal processing."""

    pass


class RebalancingService:
    """Production service for deterministic rebalancing recommendation generation, simulation, and persistence."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.analytics_service = PortfolioAnalyticsService(session)

    def _get_active_fee_tiers(self, as_of_date: date) -> list[dict]:
        """Fetch active fee schedule records effective as of date and convert to tier dicts."""
        fee_schedules = (
            self.session.query(FeeSchedule)
            .filter(
                FeeSchedule.is_active.is_(True),
                FeeSchedule.effective_from <= as_of_date,
                (
                    FeeSchedule.effective_to.is_(None)
                    | (FeeSchedule.effective_to >= as_of_date)
                ),
            )
            .order_by(FeeSchedule.fee_schedule_id)
            .all()
        )
        return [
            {
                "fee_schedule_id": f.fee_schedule_id,
                "asset_class": f.asset_class,
                "trade_side": f.trade_side,
                "min_trade_value": f.min_trade_value,
                "max_trade_value": f.max_trade_value,
                "fee_rate_bps": f.fee_rate_bps,
                "fixed_fee": f.fixed_fee,
                "minimum_fee": f.minimum_fee,
                "maximum_fee": f.maximum_fee,
                "effective_from": f.effective_from,
                "effective_to": f.effective_to,
                "is_active": f.is_active,
            }
            for f in fee_schedules
        ]

    def _get_active_excluded_instruments(self, as_of_date: date) -> set[str]:
        """Retrieve set of instrument IDs actively excluded on as_of_date."""
        constraints = (
            self.session.query(Constraint)
            .filter(
                Constraint.constraint_type == "EXCLUDED_INSTRUMENT",
                Constraint.is_active.is_(True),
                Constraint.effective_from <= as_of_date,
                (
                    Constraint.effective_to.is_(None)
                    | (Constraint.effective_to >= as_of_date)
                ),
            )
            .order_by(Constraint.constraint_id)
            .all()
        )
        excluded: set[str] = set()
        for c in constraints:
            if c.scope_type == "INSTRUMENT" and c.scope_reference_id:
                excluded.add(c.scope_reference_id)
            for inst in c.instruments:
                excluded.add(inst.instrument_id)
        return excluded

    def _get_latest_price_record(self, instrument_id: str, as_of_date: date) -> MarketPrice:
        """Resolve latest market price record on or before as_of_date or raise MissingPriceError."""
        latest_price_rec = (
            self.session.query(MarketPrice)
            .filter(
                MarketPrice.instrument_id == instrument_id,
                MarketPrice.price_date <= as_of_date,
            )
            .order_by(MarketPrice.price_date.desc(), MarketPrice.id.desc())
            .first()
        )
        if not latest_price_rec:
            raise MissingPriceError(instrument_id, as_of_date)
        return latest_price_rec

    def _get_latest_price(self, instrument_id: str, as_of_date: date) -> Decimal:
        """Resolve latest market price on or before as_of_date or raise MissingPriceError."""
        return self._get_latest_price_record(instrument_id, as_of_date).price

    def generate_rebalance_trades(
        self, portfolio_id: str, as_of_date: date
    ) -> RebalanceRecommendationResult:
        """Generate deterministic, lot-sized BUY and SELL trade recommendations."""
        # 1. Valuation and Drift
        valuation = self.analytics_service.get_portfolio_valuation(portfolio_id, as_of_date)
        drift_result = self.analytics_service.get_portfolio_drift(portfolio_id, as_of_date)

        diagnostics: list[str] = []
        validation_failures: list[str] = []
        is_executable = True
        requires_human_review = False

        # Check stale price uncertainty in current holdings
        for pos in valuation.positions:
            if pos.diagnostic:
                diagnostics.append(pos.diagnostic)
            if pos.is_stale is None and pos.price_age_days > 0:
                requires_human_review = True

        # 2. Starting cash
        starting_cash = sum(
            (p.market_value for p in valuation.positions if p.asset_class == "CASH"),
            Decimal("0.0000"),
        )

        fee_tiers = self._get_active_fee_tiers(as_of_date)
        excluded_inst_ids = self._get_active_excluded_instruments(as_of_date)

        # Index instruments by ID
        inst_records = {
            inst.instrument_id: inst
            for inst in self.session.query(Instrument).order_by(Instrument.instrument_id).all()
        }

        # Track recommended instruments to prevent duplicate or conflicting recommendations
        recommended_instrument_ids: set[str] = set()

        # 3. Separate drifts into overweight (SELL) and underweight (BUY), excluding CASH
        overweight_drifts = [
            d for d in drift_result.drifts
            if d.monetary_drift > Decimal("0.0000") and d.asset_class != "CASH"
        ]
        underweight_drifts = [
            d for d in drift_result.drifts
            if d.monetary_drift < Decimal("0.0000") and d.asset_class != "CASH"
        ]

        # Deterministic sorting by asset class name
        overweight_drifts.sort(key=lambda d: d.asset_class)
        underweight_drifts.sort(key=lambda d: d.asset_class)

        proposed_sells: list[ProposedTrade] = []
        total_sell_notional = Decimal("0.0000")
        total_sell_fees = Decimal("0.0000")

        # 4. Generate SELL recommendations
        for drift in overweight_drifts:
            target_sell_amount = drift.monetary_drift
            held_positions = [
                p for p in valuation.positions
                if p.asset_class == drift.asset_class and p.quantity > Decimal("0.0000")
            ]
            held_positions.sort(key=lambda p: p.instrument_id)

            if not held_positions:
                diagnostics.append(f"Cannot sell from {drift.asset_class}: no positions held")
                continue

            class_held_value = sum(p.market_value for p in held_positions)
            if class_held_value == Decimal("0.0000"):
                continue

            for p in held_positions:
                inst = inst_records.get(p.instrument_id)
                lot_size = inst.lot_size if inst else Decimal("1.0000")

                # Pro-rata sell share
                pos_share = (p.market_value / class_held_value) * target_sell_amount
                ideal_qty = pos_share / p.unit_price
                num_lots = int(ideal_qty // lot_size)
                sell_qty = (Decimal(num_lots) * lot_size).quantize(Decimal("0.0001"))

                # Clamp to existing held quantity
                max_lots = int(p.quantity // lot_size)
                if num_lots > max_lots:
                    sell_qty = (Decimal(max_lots) * lot_size).quantize(Decimal("0.0001"))

                if sell_qty <= Decimal("0.0000"):
                    continue

                trade_val = calculate_trade_notional(sell_qty, p.unit_price)

                # Fee matching
                tier = match_fee_tier(fee_tiers, p.asset_class, "SELL", trade_val, as_of_date)
                if not tier:
                    is_executable = False
                    trade_status = "BLOCKED"
                    fee_id = None
                    fee_amount = Decimal("0.0000")
                    diag = f"Missing applicable fee schedule for SELL on {p.instrument_id} ({p.asset_class})"
                    validation_failures.append(diag)
                else:
                    trade_status = "PROPOSED"
                    fee_id = tier["fee_schedule_id"]
                    fee_amount = calculate_trade_fee(trade_val, tier)
                    diag = None

                proposed_sells.append(
                    ProposedTrade(
                        instrument_id=p.instrument_id,
                        symbol=p.symbol,
                        instrument_name=p.instrument_name,
                        asset_class=p.asset_class,
                        trade_side="SELL",
                        quantity=sell_qty,
                        unit_price=p.unit_price,
                        trade_value=trade_val,
                        fee_amount=fee_amount,
                        fee_schedule_id=fee_id,
                        status=trade_status,
                        diagnostic=diag,
                    )
                )
                recommended_instrument_ids.add(p.instrument_id)

                # Only executable (PROPOSED) sells contribute proceeds to cash
                if trade_status == "PROPOSED":
                    total_sell_notional += trade_val
                    total_sell_fees += fee_amount

        # 5. Calculate available cash after executable sells
        available_cash = (starting_cash + total_sell_notional - total_sell_fees).quantize(Decimal("0.0001"))

        proposed_buys: list[ProposedTrade] = []
        total_buy_notional = Decimal("0.0000")
        total_buy_fees = Decimal("0.0000")

        # 6. Generate BUY recommendations
        for drift in underweight_drifts:
            if available_cash <= Decimal("0.0000"):
                diagnostics.append(f"Insufficient cash to fund purchases for {drift.asset_class}")
                break

            target_buy_amount = abs(drift.monetary_drift)

            # Determine candidate instrument
            # Preference 1: Existing eligible held instruments in this asset class not already recommended
            held_candidates = [
                p for p in valuation.positions
                if p.asset_class == drift.asset_class
                and p.instrument_id not in excluded_inst_ids
                and p.instrument_id not in recommended_instrument_ids
            ]
            held_candidates.sort(key=lambda p: p.instrument_id)

            if held_candidates:
                chosen_inst_id = held_candidates[0].instrument_id
            else:
                # Preference 2: Lowest instrument_id among active, non-excluded, unrecommended instruments
                eligible_insts = (
                    self.session.query(Instrument)
                    .filter(
                        Instrument.asset_class == drift.asset_class,
                        Instrument.is_active.is_(True),
                        ~Instrument.instrument_id.in_(excluded_inst_ids.union(recommended_instrument_ids)),
                    )
                    .order_by(Instrument.instrument_id)
                    .all()
                )
                if not eligible_insts:
                    diagnostics.append(f"No eligible, non-excluded instruments available to buy in {drift.asset_class}")
                    continue
                chosen_inst_id = eligible_insts[0].instrument_id

            inst = inst_records.get(chosen_inst_id)
            if not inst:
                continue

            price_rec = self._get_latest_price_record(chosen_inst_id, as_of_date)
            unit_price = price_rec.price
            price_age = (as_of_date - price_rec.price_date).days
            if price_age > 0:
                requires_human_review = True
                diagnostics.append(
                    f"Price for BUY candidate {chosen_inst_id} as of {price_rec.price_date} is {price_age} day(s) old relative to as-of date {as_of_date}"
                )

            lot_size = inst.lot_size

            # Size buy trade: allocate min(target_buy_amount, available_cash)
            budget = min(target_buy_amount, available_cash)
            est_qty = budget / unit_price
            num_lots = int(est_qty // lot_size)

            if num_lots <= 0:
                diagnostics.append(f"Available cash insufficient to purchase minimum 1 lot of {chosen_inst_id}")
                continue

            buy_qty = (Decimal(num_lots) * lot_size).quantize(Decimal("0.0001"))
            trade_val = calculate_trade_notional(buy_qty, unit_price)

            # Match fee tier
            tier = match_fee_tier(fee_tiers, drift.asset_class, "BUY", trade_val, as_of_date)
            if not tier:
                is_executable = False
                trade_status = "BLOCKED"
                fee_id = None
                fee_amount = Decimal("0.0000")
                diag = f"Missing applicable fee schedule for BUY on {chosen_inst_id} ({drift.asset_class})"
                validation_failures.append(diag)
            else:
                trade_status = "PROPOSED"
                fee_id = tier["fee_schedule_id"]
                fee_amount = calculate_trade_fee(trade_val, tier)
                diag = None

                # Scale down lots if notional + fee exceeds available cash
                while (trade_val + fee_amount) > available_cash and num_lots > 0:
                    num_lots -= 1
                    buy_qty = (Decimal(num_lots) * lot_size).quantize(Decimal("0.0001"))
                    trade_val = calculate_trade_notional(buy_qty, unit_price)
                    tier = match_fee_tier(fee_tiers, drift.asset_class, "BUY", trade_val, as_of_date)
                    fee_amount = calculate_trade_fee(trade_val, tier) if tier else Decimal("0.0000")

            if num_lots > 0 or trade_status == "BLOCKED":
                proposed_buys.append(
                    ProposedTrade(
                        instrument_id=chosen_inst_id,
                        symbol=inst.symbol,
                        instrument_name=inst.instrument_name,
                        asset_class=drift.asset_class,
                        trade_side="BUY",
                        quantity=buy_qty,
                        unit_price=unit_price,
                        trade_value=trade_val,
                        fee_amount=fee_amount,
                        fee_schedule_id=fee_id,
                        status=trade_status,
                        diagnostic=diag,
                    )
                )
                recommended_instrument_ids.add(chosen_inst_id)

                if trade_status == "PROPOSED":
                    total_buy_notional += trade_val
                    total_buy_fees += fee_amount
                    available_cash = (available_cash - trade_val - fee_amount).quantize(Decimal("0.0001"))

        # 7. Remaining cash (based on executable trades only)
        remaining_cash = (
            starting_cash + total_sell_notional - total_sell_fees - total_buy_notional - total_buy_fees
        ).quantize(Decimal("0.0001"))

        # 8. Residual drift calculation
        class_net_notional: dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
        for t in proposed_sells:
            if t.status == "PROPOSED":
                class_net_notional[t.asset_class] -= t.trade_value
        for t in proposed_buys:
            if t.status == "PROPOSED":
                class_net_notional[t.asset_class] += t.trade_value

        # Post-trade estimated total portfolio value = starting_value - total_fees
        post_trade_total = (
            valuation.total_market_value - total_sell_fees - total_buy_fees
        ).quantize(Decimal("0.0001"))

        residual_drifts: dict[str, Decimal] = {}
        targets = self.analytics_service._get_effective_targets(portfolio_id, as_of_date)
        all_classes = sorted(set(targets.keys()).union(set(c.asset_class for c in valuation.asset_classes)))

        if post_trade_total > Decimal("0.0000"):
            for ac in all_classes:
                if ac == "CASH":
                    post_val = remaining_cash
                else:
                    pre_val = next((c.market_value for c in valuation.asset_classes if c.asset_class == ac), Decimal("0.0000"))
                    post_val = pre_val + class_net_notional[ac]

                post_weight = ((post_val / post_trade_total) * Decimal("100.0000")).quantize(Decimal("0.0001"))
                target_w = targets.get(ac, Decimal("0.0000"))
                residual_drifts[ac] = (post_weight - target_w).quantize(Decimal("0.0001"))

        # Sort all trades deterministically: SELLs first (by instrument_id), then BUYs (by instrument_id)
        proposed_sells.sort(key=lambda t: t.instrument_id)
        proposed_buys.sort(key=lambda t: t.instrument_id)
        all_trades = proposed_sells + proposed_buys

        return RebalanceRecommendationResult(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            starting_portfolio_value=valuation.total_market_value,
            starting_cash=starting_cash,
            proposed_trades=all_trades,
            total_sell_notional=total_sell_notional,
            total_sell_fees=total_sell_fees,
            total_buy_notional=total_buy_notional,
            total_buy_fees=total_buy_fees,
            remaining_cash=remaining_cash,
            residual_drifts=residual_drifts,
            diagnostics=diagnostics,
            validation_failures=validation_failures,
            is_executable=is_executable,
            requires_human_review=requires_human_review,
        )

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

    def evaluate_constraints(
        self,
        portfolio_id: str,
        as_of_date: date,
        proposed_trades: list[ProposedTrade],
        simulation: PostTradeSimulationResult,
    ) -> tuple[list[ConstraintFinding], list[str], list[str]]:
        """Evaluate active policy constraints effective on as_of_date against trades and simulated state."""
        constraints = (
            self.session.query(Constraint)
            .filter(
                Constraint.is_active.is_(True),
                Constraint.effective_from <= as_of_date,
                (
                    Constraint.effective_to.is_(None)
                    | (Constraint.effective_to >= as_of_date)
                ),
            )
            .order_by(Constraint.constraint_id)
            .all()
        )

        findings: list[ConstraintFinding] = []
        hard_violations: list[str] = []
        warnings: list[str] = []

        for c in constraints:
            # Check applicability
            applies = False
            if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                applies = True
            elif c.scope_type == "ASSET_CLASS":
                applies = True
            elif c.scope_type == "INSTRUMENT":
                applies = True

            if not applies:
                continue

            ctype = c.constraint_type
            is_violated = False
            affected_inst_id: Optional[str] = None
            msg = ""

            # 1. EXCLUDED_INSTRUMENT
            if ctype == "EXCLUDED_INSTRUMENT":
                excluded_ids = {c.scope_reference_id} if c.scope_reference_id else set()
                for inst in c.instruments:
                    excluded_ids.add(inst.instrument_id)

                for t in proposed_trades:
                    if t.trade_side == "BUY" and t.instrument_id in excluded_ids:
                        is_violated = True
                        affected_inst_id = t.instrument_id
                        msg = f"[{c.constraint_type}] Instrument {t.instrument_id} is on the restricted exclusion list (Constraint {c.constraint_id})"
                        break

            # 2. MAX_POSITION_WEIGHT
            elif ctype == "MAX_POSITION_WEIGHT":
                if c.threshold_value is not None:
                    if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                        for p in simulation.positions:
                            if p.asset_class != "CASH" and p.post_trade_weight > c.threshold_value:
                                is_violated = True
                                affected_inst_id = p.instrument_id
                                msg = f"[{c.constraint_type}] Position {p.instrument_id} post-trade weight {p.post_trade_weight}% exceeds maximum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"
                                break
                    elif c.scope_type == "INSTRUMENT":
                        target_id = c.scope_reference_id
                        pos = next((p for p in simulation.positions if p.instrument_id == target_id), None)
                        if pos and pos.post_trade_weight > c.threshold_value:
                            is_violated = True
                            affected_inst_id = target_id
                            msg = f"[{c.constraint_type}] Position {target_id} post-trade weight {pos.post_trade_weight}% exceeds maximum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            # 3. MIN_POSITION_WEIGHT
            elif ctype == "MIN_POSITION_WEIGHT":
                if c.threshold_value is not None:
                    if c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id:
                        for p in simulation.positions:
                            if p.asset_class != "CASH" and p.post_trade_quantity > Decimal("0.0000") and p.post_trade_weight < c.threshold_value:
                                is_violated = True
                                affected_inst_id = p.instrument_id
                                msg = f"[{c.constraint_type}] Position {p.instrument_id} post-trade weight {p.post_trade_weight}% is below minimum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"
                                break
                    elif c.scope_type == "INSTRUMENT":
                        target_id = c.scope_reference_id
                        pos = next((p for p in simulation.positions if p.instrument_id == target_id), None)
                        if pos and pos.post_trade_quantity > Decimal("0.0000") and pos.post_trade_weight < c.threshold_value:
                            is_violated = True
                            affected_inst_id = target_id
                            msg = f"[{c.constraint_type}] Position {target_id} post-trade weight {pos.post_trade_weight}% is below minimum weight limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            # 4. MIN_TRADE_VALUE
            elif ctype == "MIN_TRADE_VALUE":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == t.asset_class)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.trade_value < c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} value ${t.trade_value} is below minimum trade value threshold of ${c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 5. MAX_TRADE_VALUE
            elif ctype == "MAX_TRADE_VALUE":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == t.asset_class)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.trade_value > c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} value ${t.trade_value} exceeds maximum trade value threshold of ${c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 6. MIN_TRADE_QUANTITY
            elif ctype == "MIN_TRADE_QUANTITY":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.quantity < c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} quantity {t.quantity} is below minimum trade quantity of {c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 7. MAX_TRADE_QUANTITY
            elif ctype == "MAX_TRADE_QUANTITY":
                if c.threshold_value is not None:
                    for t in proposed_trades:
                        match_trade = (
                            (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                            or (c.scope_type == "INSTRUMENT" and c.scope_reference_id == t.instrument_id)
                        )
                        if match_trade and t.quantity > c.threshold_value:
                            is_violated = True
                            affected_inst_id = t.instrument_id
                            msg = f"[{c.constraint_type}] Trade on {t.instrument_id} quantity {t.quantity} exceeds maximum trade quantity of {c.threshold_value} (Constraint {c.constraint_id})"
                            break

            # 8. LIQUIDITY_LIMIT
            elif ctype == "LIQUIDITY_LIMIT":
                if c.threshold_value is not None:
                    match_liq = (
                        (c.scope_type == "PORTFOLIO" and c.scope_reference_id == portfolio_id)
                        or (c.scope_type == "ASSET_CLASS" and c.scope_reference_id == "CASH")
                    )
                    if match_liq:
                        post_cash_pct = (
                            (simulation.post_trade_cash / simulation.post_trade_portfolio_value * Decimal("100.0000")).quantize(Decimal("0.0001"))
                            if simulation.post_trade_portfolio_value > Decimal("0.0000")
                            else Decimal("0.0000")
                        )
                        if post_cash_pct < c.threshold_value:
                            is_violated = True
                            msg = f"[{c.constraint_type}] Post-trade cash liquidity {post_cash_pct}% is below required liquidity limit of {c.threshold_value}% (Constraint {c.constraint_id})"

            if is_violated:
                if c.severity == "HARD":
                    hard_violations.append(msg)
                else:
                    warnings.append(msg)

            findings.append(
                ConstraintFinding(
                    constraint_id=c.constraint_id,
                    constraint_name=c.constraint_name,
                    constraint_type=c.constraint_type,
                    severity=c.severity,
                    scope_type=c.scope_type,
                    scope_reference_id=c.scope_reference_id,
                    threshold_value=c.threshold_value,
                    threshold_unit=c.threshold_unit,
                    is_violated=is_violated,
                    affected_instrument_id=affected_inst_id,
                    message=msg or "Within configured policy limit",
                )
            )

        return findings, hard_violations, warnings

    def create_and_persist_proposal(
        self, portfolio_id: str, as_of_date: date
    ) -> RebalanceProposalResponse:
        """Generate, simulate, validate constraints, and transactionally persist a RebalanceProposal with Trades."""
        portfolio = self.session.get(Portfolio, portfolio_id)
        if not portfolio:
            raise PortfolioNotFoundError(portfolio_id)

        # 1. Generate initial recommendations
        rebal_res = self.generate_rebalance_trades(portfolio_id, as_of_date)

        # 2. Run initial simulation
        sim_result = self.simulate_post_trade_state(portfolio_id, as_of_date, rebal_res.proposed_trades)

        # 3. Evaluate constraints
        findings, hard_violations, warnings = self.evaluate_constraints(
            portfolio_id, as_of_date, rebal_res.proposed_trades, sim_result
        )

        is_executable = True
        review_reason: Optional[str] = None

        if hard_violations:
            is_executable = False
            proposal_status = ProposalStatus.REJECTED
            review_decision = ReviewDecision.REJECTED
            review_reason = "; ".join(hard_violations)

            # Block affected trades
            violated_inst_ids = {
                f.affected_instrument_id
                for f in findings
                if f.is_violated and f.severity == "HARD" and f.affected_instrument_id
            }
            for t in rebal_res.proposed_trades:
                if t.instrument_id in violated_inst_ids:
                    t.status = "BLOCKED"
                    t.diagnostic = "Blocked by hard policy constraint violation"
        else:
            # Check if any trades were blocked during generation (e.g. missing fee schedule)
            blocked_trades = [t for t in rebal_res.proposed_trades if t.status == "BLOCKED"]
            if blocked_trades:
                is_executable = False
                proposal_status = ProposalStatus.REJECTED
                review_decision = ReviewDecision.REJECTED
                review_reason = "Proposal contains unexecutable blocked trades: missing fee schedules or invalid market conditions"
            else:
                proposal_status = ProposalStatus.PENDING_REVIEW
                review_decision = ReviewDecision.PENDING
                review_reason = None

        # Reconcile cash solvency and dependent BUY trades
        # If any SELL trade is BLOCKED, its proceeds are $0 and cannot fund BUYs
        avail_cash = rebal_res.starting_cash
        for t in rebal_res.proposed_trades:
            if t.trade_side == "SELL" and t.status == "PROPOSED":
                avail_cash += t.trade_value - t.fee_amount

        for t in rebal_res.proposed_trades:
            if t.trade_side == "BUY" and t.status == "PROPOSED":
                outlay = t.trade_value + t.fee_amount
                if outlay > avail_cash:
                    t.status = "BLOCKED"
                    t.diagnostic = "Blocked: insufficient executable proceeds to fund purchase"
                else:
                    avail_cash -= outlay

        # Re-run simulation so blocked trades (BUY and SELL) are completely excluded from final post-trade state
        sim_result = self.simulate_post_trade_state(portfolio_id, as_of_date, rebal_res.proposed_trades)

        # 4. Transactional persistence with collision retry
        from sqlalchemy.exc import IntegrityError

        now_dt = datetime.now(timezone.utc)
        year_prefix = f"RB-{as_of_date.year}-"

        for attempt in range(5):
            try:
                # Query existing proposal IDs matching year_prefix to find max numeric suffix
                existing_prop_ids = [
                    p[0]
                    for p in self.session.query(RebalanceProposal.proposal_id)
                    .filter(RebalanceProposal.proposal_id.like(f"{year_prefix}%"))
                    .all()
                ]
                max_p_seq = 0
                for pid in existing_prop_ids:
                    suffix = pid[len(year_prefix):]
                    if suffix.isdigit():
                        max_p_seq = max(max_p_seq, int(suffix))

                proposal_id = f"{year_prefix}{max_p_seq + 1:06d}"
                while self.session.get(RebalanceProposal, proposal_id) is not None:
                    max_p_seq += 1
                    proposal_id = f"{year_prefix}{max_p_seq + 1:06d}"

                db_proposal = RebalanceProposal(
                    proposal_id=proposal_id,
                    portfolio_id=portfolio_id,
                    status=proposal_status.value if hasattr(proposal_status, "value") else str(proposal_status),
                    review_decision=review_decision.value if hasattr(review_decision, "value") else str(review_decision),
                    pre_trade_portfolio_value=sim_result.pre_trade_portfolio_value,
                    post_trade_portfolio_value=sim_result.post_trade_portfolio_value,
                    created_at=now_dt,
                    reviewed_at=now_dt if proposal_status == ProposalStatus.REJECTED else None,
                    review_reason=review_reason,
                )
                self.session.add(db_proposal)
                self.session.flush()

                # Derive max numeric sequence for Trade.trade_id to prevent collision with gaps
                existing_trade_ids = [
                    t[0]
                    for t in self.session.query(Trade.trade_id)
                    .filter(Trade.trade_id.like("TRD-%"))
                    .all()
                ]
                max_t_seq = 0
                for tid in existing_trade_ids:
                    suffix = tid[4:]
                    if suffix.isdigit():
                        max_t_seq = max(max_t_seq, int(suffix))

                persisted_trade_responses: list[TradeResponse] = []

                for i, pt in enumerate(rebal_res.proposed_trades):
                    t_idx = max_t_seq + i + 1
                    trade_id = f"TRD-{t_idx:06d}"
                    while self.session.get(Trade, trade_id) is not None:
                        max_t_seq += 1
                        trade_id = f"TRD-{max_t_seq + i + 1:06d}"

                    db_trade = Trade(
                        trade_id=trade_id,
                        proposal_id=proposal_id,
                        instrument_id=pt.instrument_id,
                        fee_schedule_id=pt.fee_schedule_id,
                        trade_side=pt.trade_side,
                        quantity=pt.quantity,
                        unit_price=pt.unit_price,
                        trade_value=pt.trade_value,
                        fee_amount=pt.fee_amount,
                        status=pt.status,
                        created_at=now_dt,
                    )
                    self.session.add(db_trade)
                    persisted_trade_responses.append(
                        TradeResponse(
                            trade_id=trade_id,
                            proposal_id=proposal_id,
                            instrument_id=pt.instrument_id,
                            symbol=pt.symbol,
                            instrument_name=pt.instrument_name,
                            asset_class=pt.asset_class,
                            trade_side=pt.trade_side,
                            quantity=pt.quantity,
                            unit_price=pt.unit_price,
                            trade_value=pt.trade_value,
                            fee_amount=pt.fee_amount,
                            fee_schedule_id=pt.fee_schedule_id,
                            status=pt.status,
                            diagnostic=pt.diagnostic,
                        )
                    )

                self.session.commit()
                break
            except IntegrityError:
                self.session.rollback()
                if attempt == 4:
                    raise
            except Exception:
                self.session.rollback()
                raise

        return RebalanceProposalResponse(
            proposal_id=proposal_id,
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            status=proposal_status.value if hasattr(proposal_status, "value") else str(proposal_status),
            review_decision=review_decision.value if hasattr(review_decision, "value") else str(review_decision),
            review_reason=review_reason,
            pre_trade_portfolio_value=sim_result.pre_trade_portfolio_value,
            post_trade_portfolio_value=sim_result.post_trade_portfolio_value,
            created_at=now_dt,
            trades=persisted_trade_responses,
            simulation=sim_result,
            constraint_findings=findings,
            warnings=warnings,
            is_executable=is_executable,
            requires_human_review=rebal_res.requires_human_review,
        )
