"""Tests for synthetic dataset builder and pipeline orchestration."""

import subprocess
import sys
from pathlib import Path

from synthetic_data.dataset_builder import DatasetBuilder, build_dataset
from synthetic_data.dataset_config import STARTER_CONFIG, DatasetConfig


def test_build_starter_dataset_pipeline():
    builder = DatasetBuilder(config=STARTER_CONFIG)
    baseline, anomalous, ground_truth, report = builder.build()

    # Verify baseline keys
    expected_keys = {
        "investor_profile",
        "portfolio",
        "instrument",
        "market_price",
        "target_allocation",
        "holding",
        "fee_schedule",
        "constraint",
        "constraint_instrument",
        "rebalance_proposal",
        "trade",
    }
    assert set(baseline.keys()) == expected_keys
    assert set(anomalous.keys()) == expected_keys

    # Verify counts based on starter config
    assert len(baseline["investor_profile"]) == STARTER_CONFIG.investor_count
    assert len(baseline["portfolio"]) == STARTER_CONFIG.investor_count * STARTER_CONFIG.portfolios_per_investor
    assert len(baseline["instrument"]) == STARTER_CONFIG.instrument_count
    assert len(ground_truth) >= 5

    # Verify validation report passes reconciliation
    assert report.is_cleanly_reconciled


def test_dataset_builder_determinism():
    config1 = DatasetConfig(name="test_det", investor_count=3, instrument_count=10, seed=20261022)
    config2 = DatasetConfig(name="test_det", investor_count=3, instrument_count=10, seed=20261022)
    config3 = DatasetConfig(name="test_det", investor_count=3, instrument_count=10, seed=99999)

    b1, a1, gt1, _ = build_dataset(config1)
    b2, a2, gt2, _ = build_dataset(config2)
    b3, a3, gt3, _ = build_dataset(config3)

    assert b1 == b2
    assert a1 == a2
    assert [g.record_id for g in gt1] == [g.record_id for g in gt2]

    assert b1 != b3
    assert a1 != a3


def test_dataset_builder_cli_starter(tmp_path):
    export_dir = str(tmp_path / "cli_test")
    cmd = [
        sys.executable,
        "-m",
        "synthetic_data.dataset_builder",
        "--config",
        "starter",
        "--seed",
        "20261022",
        "--export-dir",
        export_dir,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI command failed:\n{res.stderr}\n{res.stdout}"
    assert Path(export_dir, "csv", "investor_profile.csv").exists()
    assert Path(export_dir, "csv", "ground_truth.csv").exists()
    assert Path(export_dir, "metadata.json").exists()

