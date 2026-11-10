"""Tests for synthetic dataset exporter."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from synthetic_data.dataset_builder import build_dataset
from synthetic_data.dataset_config import STARTER_CONFIG
from synthetic_data.exporters.dataset_exporter import export_dataset


def _sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_export_dataset_creates_all_expected_artifacts(tmp_path):
    output_dir = tmp_path / "export_test"
    baseline, anomalous, ground_truth, report = build_dataset(STARTER_CONFIG)

    export_dataset(
        dataset=anomalous,
        ground_truth=ground_truth,
        report=report,
        output_dir=output_dir,
        config=STARTER_CONFIG,
    )

    # 1. Check CSV files
    csv_dir = output_dir / "csv"
    assert csv_dir.exists()
    expected_tables = [
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
    ]
    for table in expected_tables:
        csv_file = csv_dir / f"{table}.csv"
        assert csv_file.exists(), f"Missing CSV for {table}"
        assert csv_file.stat().st_size > 0

    # Ground truth CSV must exist separately
    gt_csv = csv_dir / "ground_truth.csv"
    assert gt_csv.exists()
    assert gt_csv.stat().st_size > 0

    # 2. Check JSON files
    json_dir = output_dir / "json"
    assert json_dir.exists()
    for table in expected_tables:
        json_file = json_dir / f"{table}.json"
        assert json_file.exists(), f"Missing JSON for {table}"

    gt_json = json_dir / "ground_truth.json"
    assert gt_json.exists()

    # 3. Check SQL seed data
    sql_file = output_dir / "sql" / "seed_data.sql"
    assert sql_file.exists()
    sql_content = sql_file.read_text(encoding="utf-8")
    assert "INSERT INTO" in sql_content
    # Ground truth must NOT be inside SQL seed data for application tables
    assert "INSERT INTO ground_truth" not in sql_content

    # 4. Check Metadata and Manifest
    meta_file = output_dir / "metadata.json"
    assert meta_file.exists()
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    assert metadata["config_name"] == STARTER_CONFIG.name
    assert "checksums" in metadata
    assert "row_counts" in metadata

    # 5. Check README.md
    readme_file = output_dir / "README.md"
    assert readme_file.exists()
    assert "Portfolio Rebalancing System" in readme_file.read_text(encoding="utf-8")


def test_ground_truth_not_in_entity_csvs(tmp_path):
    output_dir = tmp_path / "gt_check"
    baseline, anomalous, ground_truth, report = build_dataset(STARTER_CONFIG)

    export_dataset(
        dataset=anomalous,
        ground_truth=ground_truth,
        report=report,
        output_dir=output_dir,
        config=STARTER_CONFIG,
    )

    trade_csv = (output_dir / "csv" / "trade.csv").read_text(encoding="utf-8")
    assert "issue_type" not in trade_csv
    assert "expected_decision" not in trade_csv
    assert "explanation" not in trade_csv


def test_repeated_exports_produce_identical_sha256_checksums(tmp_path):
    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"

    baseline, anomalous, ground_truth, report = build_dataset(STARTER_CONFIG)

    export_dataset(
        dataset=anomalous,
        ground_truth=ground_truth,
        report=report,
        output_dir=dir1,
        config=STARTER_CONFIG,
    )
    export_dataset(
        dataset=anomalous,
        ground_truth=ground_truth,
        report=report,
        output_dir=dir2,
        config=STARTER_CONFIG,
    )

    # 1. SQL output determinism
    sql1_hash = _sha256(dir1 / "sql" / "seed_data.sql")
    sql2_hash = _sha256(dir2 / "sql" / "seed_data.sql")
    assert sql1_hash == sql2_hash, "sql/seed_data.sql is not deterministic across runs"

    # 2. SQL checksum in metadata matches actual file
    meta1 = json.loads((dir1 / "metadata.json").read_text(encoding="utf-8"))
    assert meta1["checksums"]["sql/seed_data.sql"] == sql1_hash

    # 3. README determinism
    readme1_hash = _sha256(dir1 / "README.md")
    readme2_hash = _sha256(dir2 / "README.md")
    assert readme1_hash == readme2_hash, "README.md is not deterministic across runs"

    # 4. Metadata determinism
    meta1_hash = _sha256(dir1 / "metadata.json")
    meta2_hash = _sha256(dir2 / "metadata.json")
    assert meta1_hash == meta2_hash, "metadata.json is not deterministic across runs"

    # 5. Check all files across both exports
    files1 = {p.relative_to(dir1): _sha256(p) for p in dir1.rglob("*") if p.is_file()}
    files2 = {p.relative_to(dir2): _sha256(p) for p in dir2.rglob("*") if p.is_file()}
    assert files1 == files2, f"Artifact hashes differ between runs:\n{set(files1.items()) ^ set(files2.items())}"


def test_cli_repeated_runs_produce_identical_artifact_hashes(tmp_path):
    run_a = tmp_path / "cli_runA"
    run_b = tmp_path / "cli_runB"

    for target in (run_a, run_b):
        cmd = [
            sys.executable,
            "-m",
            "synthetic_data.dataset_builder",
            "--config",
            "starter",
            "--seed",
            "20261022",
            "--export-dir",
            str(target),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"CLI command failed:\n{res.stderr}"

    files_a = {p.relative_to(run_a): _sha256(p) for p in run_a.rglob("*") if p.is_file()}
    files_b = {p.relative_to(run_b): _sha256(p) for p in run_b.rglob("*") if p.is_file()}
    assert files_a == files_b, f"CLI repeated exports differ:\n{set(files_a.items()) ^ set(files_b.items())}"
