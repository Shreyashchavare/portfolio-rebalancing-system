"""Tests for complete synthetic dataset validator."""

from datetime import date

from synthetic_data.anomaly_injector import AnomalyInjector
from synthetic_data.generators.constraint_generator import generate_constraints
from synthetic_data.generators.fee_schedule_generator import generate_fee_schedules
from synthetic_data.generators.holding_generator import generate_holdings
from synthetic_data.generators.instrument_generator import generate_instruments
from synthetic_data.generators.investor_generator import generate_investors
from synthetic_data.generators.market_price_generator import generate_market_prices
from synthetic_data.generators.portfolio_generator import generate_portfolios
from synthetic_data.generators.rebalance_proposal_generator import generate_rebalance_proposals
from synthetic_data.generators.target_allocation_generator import generate_target_allocations
from synthetic_data.generators.trade_generator import generate_trades
from synthetic_data.validators.dataset_validator import DatasetValidator


def _build_test_dataset():
    investors = generate_investors(count=5, seed=123)
    portfolios = generate_portfolios(investors, portfolios_per_investor=2, seed=123)
    instruments = generate_instruments(count=20, seed=123)
    market_prices = generate_market_prices(
        instruments, trading_days=15, start_date=date(2026, 1, 1), seed=123
    )
    target_allocations = generate_target_allocations(portfolios, investors, seed=123)
    holdings = generate_holdings(portfolios, instruments, as_of_date=date(2026, 1, 15), seed=123)
    fee_schedules = generate_fee_schedules()
    constraints, constraint_bridge = generate_constraints(portfolios, instruments, seed=123)
    proposals = generate_rebalance_proposals(portfolios, proposals_per_portfolio=1, seed=123)
    trades = generate_trades(
        proposals,
        holdings,
        instruments,
        market_prices,
        fee_schedules,
        constraints=constraints,
        seed=123,
    )

    return {
        "investor_profile": investors,
        "portfolio": portfolios,
        "instrument": instruments,
        "market_price": market_prices,
        "target_allocation": target_allocations,
        "holding": holdings,
        "fee_schedule": fee_schedules,
        "constraint": constraints,
        "constraint_instrument": constraint_bridge,
        "rebalance_proposal": proposals,
        "trade": trades,
    }


def test_validate_baseline_dataset_passes():
    baseline = _build_test_dataset()
    validator = DatasetValidator()
    report = validator.validate_baseline(baseline)

    assert report.is_valid, f"Baseline validation failed: {[e.message for e in report.errors]}"
    assert report.error_count == 0


def test_validate_baseline_fails_on_broken_fk():
    baseline = _build_test_dataset()
    baseline["trade"][0]["instrument_id"] = "NON-EXISTENT-ID"

    validator = DatasetValidator()
    report = validator.validate_baseline(baseline)

    assert not report.is_valid
    assert any("NON-EXISTENT-ID" in e.message for e in report.errors)


def test_validate_baseline_fails_on_allocation_sum_mismatch():
    baseline = _build_test_dataset()
    from decimal import Decimal
    baseline["target_allocation"][0]["target_weight"] += Decimal("5.0000")

    validator = DatasetValidator()
    report = validator.validate_baseline(baseline)

    assert not report.is_valid
    assert any("does not sum to 100%" in e.message for e in report.errors)


def test_validate_with_ground_truth_reconciles_anomalies():
    baseline = _build_test_dataset()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_all_anomalies(baseline)

    validator = DatasetValidator()
    raw_report = validator.validate_baseline(anomalous_data)
    assert not raw_report.is_valid

    reconciliation = validator.validate_with_ground_truth(anomalous_data, ground_truth)
    assert reconciliation.is_cleanly_reconciled, f"Unreconciled errors: {reconciliation.unreconciled_errors}"
    assert len(reconciliation.matched_anomalies) == len(ground_truth)


def test_reconciliation_anomaly_count_semantics():
    baseline = _build_test_dataset()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_all_anomalies(baseline)

    validator = DatasetValidator()
    raw_report = validator.validate_baseline(anomalous_data)
    # Six raw validation errors across the five injected anomaly records
    assert len(raw_report.errors) == 6
    assert len(ground_truth) == 5

    reconciliation = validator.validate_with_ground_truth(anomalous_data, ground_truth)
    assert reconciliation.total_detected_anomalies == 5
    assert reconciliation.total_validation_errors == 6
    assert len(reconciliation.matched_anomalies) == 5
    assert len(reconciliation.unreconciled_errors) == 0
    assert reconciliation.is_cleanly_reconciled is True


def test_reconciliation_fails_on_unknown_unreconciled_error():
    from decimal import Decimal

    baseline = _build_test_dataset()
    injector = AnomalyInjector(seed=123)
    anomalous_data, ground_truth = injector.inject_all_anomalies(baseline)

    # Corrupt a non-anomalous trade that is NOT in ground truth
    gt_ids = {gt.record_id for gt in ground_truth}
    target_trade = next(t for t in anomalous_data["trade"] if t["trade_id"] not in gt_ids)
    target_trade["trade_value"] += Decimal("500.0000")

    validator = DatasetValidator()
    reconciliation = validator.validate_with_ground_truth(anomalous_data, ground_truth)

    assert reconciliation.is_cleanly_reconciled is False
    assert len(reconciliation.unreconciled_errors) > 0
    assert any(e.record_id == target_trade["trade_id"] for e in reconciliation.unreconciled_errors)
