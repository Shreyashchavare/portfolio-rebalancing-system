"""Dataset builder and orchestration pipeline for synthetic portfolio data."""

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Optional

from synthetic_data.anomaly_injector import AnomalyInjector, GroundTruthRecord
from synthetic_data.dataset_config import FULL_CONFIG, STARTER_CONFIG, DatasetConfig
from synthetic_data.exporters.dataset_exporter import export_dataset
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
from synthetic_data.validators.dataset_validator import DatasetValidator, ReconciliationReport


class DatasetBuilder:
    """Orchestrates the 14-step synthetic data generation and validation pipeline."""

    def __init__(self, config: DatasetConfig = STARTER_CONFIG) -> None:
        self.config = config
        self.validator = DatasetValidator()
        self.injector = AnomalyInjector(seed=config.seed)

    def build(
        self,
    ) -> tuple[
        dict[str, list[dict[str, Any]]],
        dict[str, list[dict[str, Any]]],
        list[GroundTruthRecord],
        ReconciliationReport,
    ]:
        """Execute the complete generation pipeline and return baseline, anomalous, and ground-truth data."""
        seed = self.config.seed

        # 1. Investors
        investors = generate_investors(count=self.config.investor_count, seed=seed)

        # 2. Portfolios
        portfolios = generate_portfolios(
            investors,
            portfolios_per_investor=self.config.portfolios_per_investor,
            seed=seed,
        )

        # 3. Instruments
        instruments = generate_instruments(count=self.config.instrument_count, seed=seed)

        # 4. Market prices
        market_prices = generate_market_prices(
            instruments,
            trading_days=self.config.trading_days,
            seed=seed,
        )

        # 5. Target allocations
        target_allocations = generate_target_allocations(
            portfolios,
            investors=investors,
            seed=seed,
        )

        # 6. Holdings
        holdings = generate_holdings(
            portfolios,
            instruments,
            min_holdings=self.config.min_holdings,
            max_holdings=self.config.max_holdings,
            seed=seed,
        )

        # 7. Fee schedules
        fee_schedules = generate_fee_schedules()

        # 8. Constraints and bridge associations
        constraints, constraint_bridge = generate_constraints(
            portfolios,
            instruments,
            seed=seed,
        )

        # 9. Derived calculations (Pre-verified in baseline logic)

        # 10. Rebalance proposals
        proposals = generate_rebalance_proposals(
            portfolios,
            proposals_per_portfolio=self.config.proposals_per_portfolio,
            seed=seed,
        )

        # 11. Trades
        trades = generate_trades(
            proposals,
            holdings,
            instruments,
            market_prices,
            fee_schedules,
            constraints=constraints,
            trades_per_proposal=self.config.trades_per_proposal,
            seed=seed,
        )

        baseline_dataset: dict[str, list[dict[str, Any]]] = {
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

        # 12. Validate baseline dataset
        baseline_report = self.validator.validate_baseline(baseline_dataset)
        if not baseline_report.is_valid:
            error_msgs = [e.message for e in baseline_report.errors]
            raise RuntimeError(f"Baseline synthetic dataset validation failed with errors: {error_msgs}")

        # 13. Inject labelled anomalies
        anomalous_dataset, ground_truth = self.injector.inject_all_anomalies(baseline_dataset)

        # 14. Validate final dataset and reconcile with ground truth
        reconciliation_report = self.validator.validate_with_ground_truth(anomalous_dataset, ground_truth)
        if not reconciliation_report.is_cleanly_reconciled:
            raise RuntimeError(
                f"Dataset reconciliation failed: {reconciliation_report.unreconciled_errors}"
            )

        return baseline_dataset, anomalous_dataset, ground_truth, reconciliation_report


def build_dataset(
    config: DatasetConfig = STARTER_CONFIG,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    list[GroundTruthRecord],
    ReconciliationReport,
]:
    """Convenience function to build dataset with given configuration."""
    builder = DatasetBuilder(config=config)
    return builder.build()


def main() -> None:
    """CLI entrypoint for dataset generation and export."""
    parser = argparse.ArgumentParser(description="Synthetic Portfolio Dataset Generator")
    parser.add_argument(
        "--config",
        choices=["starter", "full"],
        default="starter",
        help="Configuration profile (starter or full)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic random seed (default: 20261022)",
    )
    parser.add_argument(
        "--export-dir",
        type=str,
        default=None,
        help="Target directory to export CSV, JSON, SQL and metadata",
    )
    args = parser.parse_args()

    base_config = STARTER_CONFIG if args.config == "starter" else FULL_CONFIG
    # Create configuration with CLI seed override
    config = DatasetConfig(
        name=base_config.name,
        investor_count=base_config.investor_count,
        portfolios_per_investor=base_config.portfolios_per_investor,
        instrument_count=base_config.instrument_count,
        trading_days=base_config.trading_days,
        proposals_per_portfolio=base_config.proposals_per_portfolio,
        trades_per_proposal=base_config.trades_per_proposal,
        min_holdings=base_config.min_holdings,
        max_holdings=base_config.max_holdings,
        seed=args.seed,
    )

    print(f"Building synthetic dataset '{config.name}' (seed: {config.seed})...")
    builder = DatasetBuilder(config=config)
    baseline, anomalous, ground_truth, report = builder.build()
    print(f"Dataset successfully built and reconciled! {len(ground_truth)} anomalies labelled.")

    export_path = args.export_dir or f"data/{config.name}"
    print(f"Exporting artifacts to {export_path}...")
    metadata = export_dataset(
        dataset=anomalous,
        ground_truth=ground_truth,
        report=report,
        output_dir=export_path,
        config=config,
    )
    print("Export complete.")
    for table, count in metadata["row_counts"].items():
        print(f"  - {table}: {count} records")


if __name__ == "__main__":
    main()

