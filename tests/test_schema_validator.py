"""Tests for synthetic data schema validation framework.

Following Test-Driven Development (TDD), these tests define the specifications
and contracts for schema validation before implementation.
"""

from datetime import date
from decimal import Decimal
import pytest


def _import_schema_validator():
    """Dynamically import SchemaValidator and validation result types."""
    from synthetic_data.validators.schema_validator import (
        SchemaValidator,
        ValidationErrorDetail,
        ValidationResult,
    )

    return {
        "SchemaValidator": SchemaValidator,
        "ValidationResult": ValidationResult,
        "ValidationErrorDetail": ValidationErrorDetail,
    }


# ==============================================================================
# Required Fields & Nullability Tests
# ==============================================================================


def test_validate_required_fields_all_present():
    """Verify validation passes when all required fields are present and not None."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"investor_id": "INV-000001", "name": "Alice", "risk_category": "LOW"},
        {"investor_id": "INV-000002", "name": "Bob", "risk_category": "HIGH"},
    ]

    result = validator.validate_required_fields(
        records=records,
        required_fields=["investor_id", "name", "risk_category"],
        record_id_field="investor_id",
    )

    assert result.passed is True
    assert result.error_count == 0
    assert len(result.errors) == 0
    assert result.validation_name == "required_fields"


def test_validate_required_fields_missing_or_none():
    """Verify missing keys or None values are flagged with structured error details."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"investor_id": "INV-000001", "name": None, "risk_category": "LOW"},
        {"investor_id": "INV-000002", "risk_category": "HIGH"},  # 'name' key missing
    ]

    result = validator.validate_required_fields(
        records=records,
        required_fields=["investor_id", "name"],
        record_id_field="investor_id",
    )

    assert result.passed is False
    assert result.error_count == 2
    assert len(result.errors) == 2
    assert result.errors[0].field == "name"
    assert result.errors[0].record_id == "INV-000001"
    assert result.errors[1].record_id == "INV-000002"


# ==============================================================================
# Primary Key & Uniqueness Tests
# ==============================================================================


def test_validate_primary_key_uniqueness_pass():
    """Verify uniqueness validation passes on distinct primary keys."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"portfolio_id": "PORT-01", "name": "Core Equities"},
        {"portfolio_id": "PORT-02", "name": "Fixed Income"},
    ]

    result = validator.validate_primary_key_uniqueness(
        records=records,
        pk_field="portfolio_id",
    )

    assert result.passed is True
    assert result.error_count == 0


def test_validate_primary_key_uniqueness_duplicate():
    """Verify duplicate primary keys are flagged with offending record identifiers."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"portfolio_id": "PORT-01", "name": "First"},
        {"portfolio_id": "PORT-02", "name": "Second"},
        {"portfolio_id": "PORT-01", "name": "Duplicate First"},
    ]

    result = validator.validate_primary_key_uniqueness(
        records=records,
        pk_field="portfolio_id",
    )

    assert result.passed is False
    assert result.error_count >= 1
    assert any(err.value == "PORT-01" for err in result.errors)


def test_validate_composite_uniqueness():
    """Verify composite uniqueness validation on tuple of fields."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"portfolio_id": "PORT-1", "instrument_id": "INS-1", "date": "2026-01-01"},
        {"portfolio_id": "PORT-1", "instrument_id": "INS-1", "date": "2026-01-02"},  # Different date
        {"portfolio_id": "PORT-1", "instrument_id": "INS-1", "date": "2026-01-01"},  # Duplicate
    ]

    result = validator.validate_composite_uniqueness(
        records=records,
        fields=["portfolio_id", "instrument_id", "date"],
    )

    assert result.passed is False
    assert result.error_count == 1


# ==============================================================================
# Foreign Key Integrity Tests
# ==============================================================================


def test_validate_foreign_key_integrity_valid():
    """Verify valid foreign keys referencing existing parents pass."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    parents = [{"investor_id": "INV-1"}, {"investor_id": "INV-2"}]
    children = [
        {"portfolio_id": "P-1", "investor_id": "INV-1"},
        {"portfolio_id": "P-2", "investor_id": "INV-2"},
    ]

    result = validator.validate_foreign_key_integrity(
        child_records=children,
        fk_field="investor_id",
        parent_records=parents,
        parent_pk_field="investor_id",
    )

    assert result.passed is True
    assert result.error_count == 0


def test_validate_foreign_key_integrity_invalid_reference():
    """Verify child pointing to nonexistent parent is flagged."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    parents = [{"investor_id": "INV-1"}]
    children = [
        {"portfolio_id": "P-1", "investor_id": "INV-1"},
        {"portfolio_id": "P-2", "investor_id": "NONEXISTENT-INV"},
    ]

    result = validator.validate_foreign_key_integrity(
        child_records=children,
        fk_field="investor_id",
        parent_records=parents,
        parent_pk_field="investor_id",
        child_id_field="portfolio_id",
    )

    assert result.passed is False
    assert result.error_count == 1
    assert result.errors[0].value == "NONEXISTENT-INV"
    assert result.errors[0].record_id == "P-2"


def test_validate_foreign_key_integrity_allow_null():
    """Verify nullable foreign key (e.g. fee_schedule_id) passes when None if allow_null=True."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    parents = [{"fee_schedule_id": "FEE-1"}]
    children = [
        {"trade_id": "TR-1", "fee_schedule_id": "FEE-1"},
        {"trade_id": "TR-2", "fee_schedule_id": None},
    ]

    result = validator.validate_foreign_key_integrity(
        child_records=children,
        fk_field="fee_schedule_id",
        parent_records=parents,
        parent_pk_field="fee_schedule_id",
        allow_null=True,
    )

    assert result.passed is True
    assert result.error_count == 0


# ==============================================================================
# Enum & Domain Value Tests
# ==============================================================================


def test_validate_allowed_enum_values():
    """Verify allowed values pass and invalid strings are flagged."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"trade_id": "T1", "trade_side": "BUY"},
        {"trade_id": "T2", "trade_side": "SELL"},
        {"trade_id": "T3", "trade_side": "HOLD"},  # Invalid
    ]

    result = validator.validate_enum_values(
        records=records,
        field_name="trade_side",
        allowed_values={"BUY", "SELL"},
        record_id_field="trade_id",
    )

    assert result.passed is False
    assert result.error_count == 1
    assert result.errors[0].value == "HOLD"
    assert result.errors[0].record_id == "T3"


# ==============================================================================
# Date Ordering Tests
# ==============================================================================


def test_validate_date_ordering():
    """Verify start <= end date ordering validation."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    records = [
        {"id": "1", "effective_from": date(2026, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "2", "effective_from": date(2026, 1, 1), "effective_to": date(2026, 1, 1)},  # Equal allowed
        {"id": "3", "effective_from": date(2026, 1, 1), "effective_to": None},  # Null allowed
        {"id": "4", "effective_from": date(2026, 6, 1), "effective_to": date(2026, 5, 31)},  # Inverted
    ]

    result = validator.validate_date_ordering(
        records=records,
        start_date_field="effective_from",
        end_date_field="effective_to",
        allow_equal=True,
        allow_null_end=True,
        record_id_field="id",
    )

    assert result.passed is False
    assert result.error_count == 1
    assert result.errors[0].record_id == "4"


# ==============================================================================
# Numeric Bounds & Precision Tests
# ==============================================================================


def test_validate_numeric_bounds():
    """Verify strictly positive and range bounds on numeric/Decimal values."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    # Strictly positive test (> 0)
    qty_records = [
        {"trade_id": "T1", "quantity": Decimal("10.0")},
        {"trade_id": "T2", "quantity": Decimal("0.0")},  # Invalid for strictly positive
        {"trade_id": "T3", "quantity": Decimal("-5.0")},  # Invalid
    ]
    res_qty = validator.validate_numeric_bounds(
        records=qty_records,
        field_name="quantity",
        strictly_positive=True,
        record_id_field="trade_id",
    )
    assert res_qty.passed is False
    assert res_qty.error_count == 2

    # Percentage range test (0 <= weight <= 100)
    weight_records = [
        {"id": "W1", "weight": Decimal("0.0000")},
        {"id": "W2", "weight": Decimal("100.0000")},
        {"id": "W3", "weight": Decimal("100.0001")},  # Over 100
        {"id": "W4", "weight": Decimal("-0.0001")},  # Under 0
    ]
    res_wt = validator.validate_numeric_bounds(
        records=weight_records,
        field_name="weight",
        min_value=Decimal("0.0"),
        max_value=Decimal("100.0"),
        record_id_field="id",
    )
    assert res_wt.passed is False
    assert res_wt.error_count == 2


# ==============================================================================
# Empty Dataset Tests
# ==============================================================================


def test_empty_datasets_handled_cleanly():
    """Verify empty dataset returns passing result without error."""
    models = _import_schema_validator()
    validator = models["SchemaValidator"]()

    empty = []
    res_req = validator.validate_required_fields(empty, ["col1"])
    assert res_req.passed is True
    assert res_req.error_count == 0

    res_pk = validator.validate_primary_key_uniqueness(empty, "id")
    assert res_pk.passed is True
    assert res_pk.error_count == 0

    res_fk = validator.validate_foreign_key_integrity(empty, "fk", [], "id")
    assert res_fk.passed is True
    assert res_fk.error_count == 0

