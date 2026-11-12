"""Deterministic trade recommendation generator converting allocation drift into lot-sized orders.

Implements proportional sell sizing, priority buy candidate selection, lot-size multiples,
tiered transaction fee matching, cash solvency constraints, and residual drift computation.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.constraint import Constraint
from app.models.fee_schedule import FeeSchedule
from app.models.instrument import Instrument
from app.models.market_price import MarketPrice
from app.schemas.rebalancing import (
    ProposedTrade,
    RebalanceRecommendationResult,
)
from app.services.portfolio_analytics_service import (
    MissingPriceError,
    PortfolioAnalyticsService,
)
from synthetic_data.calculations import (
    calculate_trade_fee,
    calculate_trade_notional,
    match_fee_tier,
)


class TradeGenerator:
    """Generates deterministic, lot-sized BUY and SELL trades to reconcile portfolio allocation drift."""

    def __init__(
        self,
        session: Session,
        analytics_service: Optional[PortfolioAnalyticsService] = None,
    ) -> None:
        self.session = session
        self.analytics_service = analytics_service or PortfolioAnalyticsService(session)

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

