"""Comprehensive relational and policy dataset validator for synthetic portfolio data."""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from synthetic_data.anomaly_injector import GroundTruthRecord, IssueType
from synthetic_data.calculations import calculate_trade_notional
from synthetic_data.validators.schema_validator import SchemaValidator, ValidationErrorDetail, ValidationResult


@dataclass
class DatasetValidationReport:
    """Overall dataset validation outcome."""

    is_valid: bool
    error_count: int
    errors: list[ValidationErrorDetail] = field(default_factory=list)


@dataclass
class ReconciliationReport:
    """Reconciliation report matching validation errors with injected ground truth."""

    is_cleanly_reconciled: bool
    total_detected_anomalies: int
    matched_anomalies: list[GroundTruthRecord] = field(default_factory=list)
    unreconciled_errors: list[ValidationErrorDetail] = field(default_factory=list)


class DatasetValidator:
    """End-to-end relational, financial, and policy validator across the complete dataset."""

    def __init__(self) -> None:
        self.schema_validator = SchemaValidator()

    def validate_baseline(
        self, dataset: Mapping[str, Sequence[Mapping[str, Any]]]
    ) -> DatasetValidationReport:
        """Validate entire relational integrity, arithmetic consistency, and policy adherence."""
        all_errors: list[ValidationErrorDetail] = []

        investors = dataset.get("investor_profile", [])
        portfolios = dataset.get("portfolio", [])
        instruments = dataset.get("instrument", [])
        prices = dataset.get("market_price", [])
        allocations = dataset.get("target_allocation", [])
        holdings = dataset.get("holding", [])
        fees = dataset.get("fee_schedule", [])
        constraints = dataset.get("constraint", [])
        bridge = dataset.get("constraint_instrument", [])
        proposals = dataset.get("rebalance_proposal", [])
        trades = dataset.get("trade", [])

        # 1. Primary key uniqueness
        pk_checks = [
            (investors, "investor_id"),
            (portfolios, "portfolio_id"),
            (instruments, "instrument_id"),
            (holdings, "holding_id"),
            (fees, "fee_schedule_id"),
            (constraints, "constraint_id"),
            (proposals, "proposal_id"),
            (trades, "trade_id"),
        ]
        for data, pk in pk_checks:
            res = self.schema_validator.validate_primary_key_uniqueness(data, pk)
            if not res.passed:
                all_errors.extend(res.errors)

        # Bridge composite PK
        bridge_res = self.schema_validator.validate_composite_uniqueness(bridge, ["constraint_id", "instrument_id"])
        if not bridge_res.passed:
            all_errors.extend(bridge_res.errors)

        # 2. Foreign Key Integrity
        fk_checks = [
            (portfolios, "investor_id", investors, "investor_id", "portfolio_id", False),
            (holdings, "portfolio_id", portfolios, "portfolio_id", "holding_id", False),
            (holdings, "instrument_id", instruments, "instrument_id", "holding_id", False),
            (prices, "instrument_id", instruments, "instrument_id", None, False),
            (allocations, "portfolio_id", portfolios, "portfolio_id", None, False),
            (bridge, "constraint_id", constraints, "constraint_id", None, False),
            (bridge, "instrument_id", instruments, "instrument_id", None, False),
            (proposals, "portfolio_id", portfolios, "portfolio_id", "proposal_id", False),
            (trades, "proposal_id", proposals, "proposal_id", "trade_id", False),
            (trades, "instrument_id", instruments, "instrument_id", "trade_id", False),
            (trades, "fee_schedule_id", fees, "fee_schedule_id", "trade_id", True),
        ]
        for child, fk, parent, pk, child_id, allow_null in fk_checks:
            res = self.schema_validator.validate_foreign_key_integrity(
                child, fk, parent, pk, child_id_field=child_id, allow_null=allow_null
            )
            if not res.passed:
                all_errors.extend(res.errors)

        # 3. Target Allocations Sum = 100.0000% per portfolio
        alloc_by_portfolio = defaultdict(list)
        for a in allocations:
            alloc_by_portfolio[a["portfolio_id"]].append(a)

        for p_id, p_allocs in alloc_by_portfolio.items():
            total_weight = sum(a["target_weight"] for a in p_allocs)
            if total_weight != Decimal("100.0000"):
                all_errors.append(
                    ValidationErrorDetail(
                        row_index=None,
                        field="target_weight",
                        value=total_weight,
                        message=f"Target allocation for portfolio {p_id} does not sum to 100% (got {total_weight}%)",
                        record_id=str(p_allocs[0].get("id", p_id)),
                    )
                )

        # 4. Trade Arithmetic and Holdings Checks
        proposal_portfolio_map = {p["proposal_id"]: p["portfolio_id"] for p in proposals}
        holding_map = {
            (h["portfolio_id"], h["instrument_id"]): h["quantity"] for h in holdings
        }

        # Latest market prices
        latest_prices: dict[str, Decimal] = {}
        for p in prices:
            inst_id = p["instrument_id"]
            latest_prices[inst_id] = p["price"]

        # Active excluded instruments
        excluded_instruments = {
            c["scope_reference_id"]
            for c in constraints
            if c["constraint_type"] == "EXCLUDED_INSTRUMENT" and c.get("is_active", True)
        }

        for idx, t in enumerate(trades):
            t_id = t["trade_id"]
            qty = t["quantity"]
            price = t["unit_price"]
            val = t["trade_value"]
            fee = t.get("fee_amount", Decimal("0"))
            side = t["trade_side"]
            inst_id = t["instrument_id"]
            p_id = proposal_portfolio_map.get(t["proposal_id"])

            # Check notional arithmetic
            expected_val = calculate_trade_notional(qty, price)
            if val != expected_val:
                all_errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field="trade_value",
                        value=val,
                        message=f"Trade {t_id} trade_value {val} != qty * unit_price {expected_val}",
                        record_id=t_id,
                    )
                )

            # Check SELL quantity against holdings
            if side == "SELL" and p_id:
                held_qty = holding_map.get((p_id, inst_id), Decimal("0.0000"))
                if qty > held_qty:
                    all_errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field="quantity",
                            value=qty,
                            message=f"Trade {t_id} sell quantity {qty} exceeds available holding {held_qty}",
                            record_id=t_id,
                        )
                    )

            # Check EXCLUDED_INSTRUMENT
            if side == "BUY" and inst_id in excluded_instruments:
                all_errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field="instrument_id",
                        value=inst_id,
                        message=f"Trade {t_id} recommends excluded restricted instrument {inst_id}",
                        record_id=t_id,
                    )
                )

            # Check fee omission
            if fee == Decimal("0.0000") and val > Decimal("0.0000"):
                all_errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field="fee_amount",
                        value=fee,
                        message=f"Trade {t_id} has zero fee amount for non-zero notional {val}",
                        record_id=t_id,
                    )
                )

            # Check stale price
            latest_price = latest_prices.get(inst_id)
            if latest_price is not None and price != latest_price:
                all_errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field="unit_price",
                        value=price,
                        message=f"Trade {t_id} uses price {price} different from latest market price {latest_price}",
                        record_id=t_id,
                    )
                )

        return DatasetValidationReport(
            is_valid=(len(all_errors) == 0),
            error_count=len(all_errors),
            errors=all_errors,
        )

    def validate_with_ground_truth(
        self,
        dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        ground_truth: Sequence[GroundTruthRecord],
    ) -> ReconciliationReport:
        """Reconcile dataset validation errors against the ground-truth anomaly list."""
        report = self.validate_baseline(dataset)

        gt_by_id = {gt.record_id: gt for gt in ground_truth}
        matched: list[GroundTruthRecord] = []
        unreconciled: list[ValidationErrorDetail] = []

        for err in report.errors:
            rec_id = err.record_id
            if rec_id and rec_id in gt_by_id:
                gt = gt_by_id[rec_id]
                if gt not in matched:
                    matched.append(gt)
            else:
                unreconciled.append(err)

        is_reconciled = (len(unreconciled) == 0) and (len(matched) == len(ground_truth))

        return ReconciliationReport(
            is_cleanly_reconciled=is_reconciled,
            total_detected_anomalies=len(report.errors),
            matched_anomalies=matched,
            unreconciled_errors=unreconciled,
        )

