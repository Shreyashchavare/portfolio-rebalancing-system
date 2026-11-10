"""Reproducible dataset exporter for CSV, JSON, and SQL seed files."""

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from synthetic_data.anomaly_injector import GroundTruthRecord
from synthetic_data.dataset_config import DatasetConfig
from synthetic_data.validators.dataset_validator import ReconciliationReport


def _json_default(obj: Any) -> Any:
    """Format dates and Decimals cleanly for JSON export."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, GroundTruthRecord):
        return obj.to_dict()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _format_sql_value(val: Any) -> str:
    """Format python value into SQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, (datetime, date)):
        return f"'{val.isoformat()}'"
    # String escaping
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def _compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def export_dataset(
    dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    ground_truth: Sequence[GroundTruthRecord],
    report: Optional[ReconciliationReport],
    output_dir: Path | str,
    config: Optional[DatasetConfig] = None,
) -> dict[str, Any]:
    """Export the synthetic dataset across CSV, JSON, and SQL formats deterministically."""
    out_path = Path(output_dir)
    csv_dir = out_path / "csv"
    json_dir = out_path / "json"
    sql_dir = out_path / "sql"

    for d in (csv_dir, json_dir, sql_dir):
        d.mkdir(parents=True, exist_ok=True)

    row_counts: dict[str, int] = {}
    checksums: dict[str, str] = {}

    ref_date = getattr(config, "dataset_reference_date", "2026-01-15") if config else "2026-01-15"
    build_ts = getattr(config, "reproducible_build_timestamp", "2026-01-15T00:00:00Z") if config else "2026-01-15T00:00:00Z"

    # 1. Export entity CSVs
    for table_name, records in dataset.items():
        row_counts[table_name] = len(records)
        csv_file = csv_dir / f"{table_name}.csv"
        if records:
            headers = list(records[0].keys())
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for rec in records:
                    formatted_row = {}
                    for k, v in rec.items():
                        if isinstance(v, (datetime, date)):
                            formatted_row[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            formatted_row[k] = str(v)
                        elif v is None:
                            formatted_row[k] = ""
                        else:
                            formatted_row[k] = str(v)
                    writer.writerow(formatted_row)
        else:
            csv_file.write_text("", encoding="utf-8")
        checksums[f"csv/{table_name}.csv"] = _compute_file_sha256(csv_file)

    # Export Ground Truth CSV separately
    gt_csv = csv_dir / "ground_truth.csv"
    gt_dicts = [gt.to_dict() if hasattr(gt, "to_dict") else dict(gt) for gt in ground_truth]
    row_counts["ground_truth"] = len(gt_dicts)
    if gt_dicts:
        gt_headers = list(gt_dicts[0].keys())
        with open(gt_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=gt_headers)
            writer.writeheader()
            writer.writerows(gt_dicts)
    else:
        gt_csv.write_text("", encoding="utf-8")
    checksums["csv/ground_truth.csv"] = _compute_file_sha256(gt_csv)

    # 2. Export JSON files
    for table_name, records in dataset.items():
        json_file = json_dir / f"{table_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(records, f, default=_json_default, indent=2)
        checksums[f"json/{table_name}.json"] = _compute_file_sha256(json_file)

    gt_json = json_dir / "ground_truth.json"
    with open(gt_json, "w", encoding="utf-8") as f:
        json.dump(gt_dicts, f, default=_json_default, indent=2)
    checksums["json/ground_truth.json"] = _compute_file_sha256(gt_json)

    # 3. Export SQL Seed Script
    sql_file = sql_dir / "seed_data.sql"
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("-- Synthetic Data Seed Script for Portfolio Rebalancing System\n")
        f.write(f"-- Dataset Reference Date: {ref_date} (Deterministic Seed Export)\n\n")

        # Insertion order preserving foreign keys
        table_order = [
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

        for tbl in table_order:
            tbl_records = dataset.get(tbl, [])
            if not tbl_records:
                continue
            cols = list(tbl_records[0].keys())
            f.write(f"-- Table: {tbl} ({len(tbl_records)} rows)\n")
            for rec in tbl_records:
                vals = [_format_sql_value(rec.get(col)) for col in cols]
                cols_str = ", ".join(cols)
                vals_str = ", ".join(vals)
                f.write(f"INSERT INTO {tbl} ({cols_str}) VALUES ({vals_str});\n")
            f.write("\n")
    checksums["sql/seed_data.sql"] = _compute_file_sha256(sql_file)

    # 4. Metadata and validation summary
    metadata = {
        "config_name": config.name if config else "custom",
        "seed": config.seed if config else 20261022,
        "dataset_reference_date": ref_date,
        "reproducible_build_timestamp": build_ts,
        "row_counts": row_counts,
        "checksums": checksums,
    }
    meta_file = out_path / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    val_summary = {
        "is_cleanly_reconciled": report.is_cleanly_reconciled if report else True,
        "total_anomalies": report.total_detected_anomalies if report else len(ground_truth),
        "unreconciled_errors": [
            {"field": e.field, "value": str(e.value), "message": e.message}
            for e in (report.unreconciled_errors if report else [])
        ],
    }
    val_file = out_path / "validation_summary.json"
    with open(val_file, "w", encoding="utf-8") as f:
        json.dump(val_summary, f, indent=2)

    # 5. README.md
    readme_content = f"""# Portfolio Rebalancing System — Synthetic Dataset

Generated by the synthetic data generation pipeline.

- **Configuration:** {config.name if config else "custom"}
- **Random Seed:** {config.seed if config else 20261022}
- **Dataset Reference Date:** {ref_date}
- **Reproducible Build Timestamp:** {build_ts}
- **Reconciliation Status:** {"CLEANLY RECONCILED" if val_summary["is_cleanly_reconciled"] else "UNRECONCILED ERRORS"}

## Artifact Directory Structure

- `csv/`: Individual comma-separated files per database table.
- `json/`: Individual JSON files per table.
- `sql/seed_data.sql`: Relational SQL INSERT statements for PostgreSQL or SQLite.
- `csv/ground_truth.csv` & `json/ground_truth.json`: Challenge anomaly labels, kept separate from model features.
- `metadata.json`: Generation metadata and SHA-256 checksums.
- `validation_summary.json`: Integrity validation results.

## Summary Table Counts

| Entity Table | Record Count |
|---|---|
"""
    for tbl, count in row_counts.items():
        readme_content += f"| `{tbl}` | {count} |\n"

    readme_file = out_path / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")

    return metadata
