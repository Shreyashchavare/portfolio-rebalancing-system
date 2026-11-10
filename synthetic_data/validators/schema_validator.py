"""Reusable schema validation framework for synthetic data."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Optional, Sequence, Union


@dataclass(frozen=True)
class ValidationErrorDetail:
    """Detailed record-level error metadata."""

    row_index: Optional[int]
    field: Optional[str]
    value: Any
    message: str
    record_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Structured result of a schema validation check."""

    validation_name: str
    passed: bool
    error_count: int
    errors: list[ValidationErrorDetail] = field(default_factory=list)


def _to_record_list(data: Any) -> list[dict[str, Any]]:
    """Convert supported input structures (list of dicts, Pandas DataFrame, etc.) into list of dicts."""
    if data is None:
        return []
    if hasattr(data, "to_dict") and callable(data.to_dict):
        # Pandas DataFrame compatibility
        return data.to_dict(orient="records")
    if isinstance(data, list):
        return [dict(item) if isinstance(item, dict) else item for item in data]
    return list(data)


class SchemaValidator:
    """Validation framework providing modular validation rules for synthetic datasets."""

    def validate_required_fields(
        self,
        records: Any,
        required_fields: Sequence[str],
        record_id_field: Optional[str] = None,
    ) -> ValidationResult:
        """Validate that all required fields are present in each record and not None."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        for idx, rec in enumerate(recs):
            rec_id = rec.get(record_id_field) if record_id_field else None
            for req_field in required_fields:
                if req_field not in rec or rec[req_field] is None:
                    errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field=req_field,
                            value=rec.get(req_field),
                            message=f"Required field '{req_field}' is missing or None",
                            record_id=str(rec_id) if rec_id is not None else None,
                        )
                    )

        return ValidationResult(
            validation_name="required_fields",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_primary_key_uniqueness(
        self,
        records: Any,
        pk_field: str,
    ) -> ValidationResult:
        """Validate that primary key values are unique across all records."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        seen_keys: set[Any] = set()

        for idx, rec in enumerate(recs):
            val = rec.get(pk_field)
            if val in seen_keys:
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=pk_field,
                        value=val,
                        message=f"Duplicate primary key value '{val}' for field '{pk_field}'",
                        record_id=str(val) if val is not None else None,
                    )
                )
            else:
                seen_keys.add(val)

        return ValidationResult(
            validation_name="primary_key_uniqueness",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_composite_uniqueness(
        self,
        records: Any,
        fields: Sequence[str],
        record_id_field: Optional[str] = None,
    ) -> ValidationResult:
        """Validate that the combination of specified fields is unique across records."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        seen_tuples: set[tuple] = set()

        for idx, rec in enumerate(recs):
            key_tuple = tuple(rec.get(f) for f in fields)
            if key_tuple in seen_tuples:
                rec_id = rec.get(record_id_field) if record_id_field else None
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=",".join(fields),
                        value=key_tuple,
                        message=f"Duplicate composite key {key_tuple} across fields {list(fields)}",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )
            else:
                seen_tuples.add(key_tuple)

        return ValidationResult(
            validation_name="composite_uniqueness",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_foreign_key_integrity(
        self,
        child_records: Any,
        fk_field: str,
        parent_records: Any,
        parent_pk_field: str,
        child_id_field: Optional[str] = None,
        allow_null: bool = False,
    ) -> ValidationResult:
        """Validate that child foreign keys reference existing parent primary keys."""
        children = _to_record_list(child_records)
        parents = _to_record_list(parent_records)

        parent_keys = {
            p[parent_pk_field]
            for p in parents
            if parent_pk_field in p and p[parent_pk_field] is not None
        }

        errors: list[ValidationErrorDetail] = []

        for idx, child in enumerate(children):
            fk_val = child.get(fk_field)
            if fk_val is None:
                if not allow_null:
                    rec_id = child.get(child_id_field) if child_id_field else None
                    errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field=fk_field,
                            value=None,
                            message=f"Non-nullable foreign key '{fk_field}' is None",
                            record_id=str(rec_id) if rec_id is not None else None,
                        )
                    )
                continue

            if fk_val not in parent_keys:
                rec_id = child.get(child_id_field) if child_id_field else None
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=fk_field,
                        value=fk_val,
                        message=f"Foreign key '{fk_field}' value '{fk_val}' not found in parent table '{parent_pk_field}'",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )

        return ValidationResult(
            validation_name="foreign_key_integrity",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_enum_values(
        self,
        records: Any,
        field_name: str,
        allowed_values: Union[set, Sequence, type[Enum]],
        record_id_field: Optional[str] = None,
        allow_null: bool = False,
    ) -> ValidationResult:
        """Validate that field values belong to the set of allowed enum values."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        if isinstance(allowed_values, type) and issubclass(allowed_values, Enum):
            valid_set = {e.value for e in allowed_values} | {e for e in allowed_values}
        else:
            valid_set = set(allowed_values)

        for idx, rec in enumerate(recs):
            val = rec.get(field_name)
            if val is None:
                if not allow_null:
                    rec_id = rec.get(record_id_field) if record_id_field else None
                    errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field=field_name,
                            value=None,
                            message=f"Field '{field_name}' value cannot be None",
                            record_id=str(rec_id) if rec_id is not None else None,
                        )
                    )
                continue

            # Compare value or enum value
            raw_val = val.value if hasattr(val, "value") else val
            if raw_val not in valid_set and val not in valid_set:
                rec_id = rec.get(record_id_field) if record_id_field else None
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=field_name,
                        value=val,
                        message=f"Value '{val}' for field '{field_name}' not in allowed values: {sorted(list(valid_set), key=str)}",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )

        return ValidationResult(
            validation_name="enum_values",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_date_ordering(
        self,
        records: Any,
        start_date_field: str,
        end_date_field: str,
        allow_equal: bool = True,
        allow_null_end: bool = True,
        record_id_field: Optional[str] = None,
    ) -> ValidationResult:
        """Validate that end date is on or after start date."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        for idx, rec in enumerate(recs):
            start = rec.get(start_date_field)
            end = rec.get(end_date_field)

            if start is None:
                continue

            if end is None:
                if not allow_null_end:
                    rec_id = rec.get(record_id_field) if record_id_field else None
                    errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field=end_date_field,
                            value=None,
                            message=f"End date '{end_date_field}' cannot be None",
                            record_id=str(rec_id) if rec_id is not None else None,
                        )
                    )
                continue

            # Compare start and end
            is_valid = (end >= start) if allow_equal else (end > start)
            if not is_valid:
                rec_id = rec.get(record_id_field) if record_id_field else None
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=f"{start_date_field}->{end_date_field}",
                        value=(start, end),
                        message=f"End date {end} is before start date {start} (allow_equal={allow_equal})",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )

        return ValidationResult(
            validation_name="date_ordering",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )

    def validate_numeric_bounds(
        self,
        records: Any,
        field_name: str,
        min_value: Optional[Union[Decimal, int, float]] = None,
        max_value: Optional[Union[Decimal, int, float]] = None,
        strictly_positive: bool = False,
        nonnegative: bool = False,
        allow_null: bool = False,
        record_id_field: Optional[str] = None,
    ) -> ValidationResult:
        """Validate numeric constraints such as strictly positive (> 0), nonnegative (>= 0), or min/max ranges."""
        recs = _to_record_list(records)
        errors: list[ValidationErrorDetail] = []

        for idx, rec in enumerate(recs):
            val = rec.get(field_name)

            if val is None:
                if not allow_null:
                    rec_id = rec.get(record_id_field) if record_id_field else None
                    errors.append(
                        ValidationErrorDetail(
                            row_index=idx,
                            field=field_name,
                            value=None,
                            message=f"Numeric field '{field_name}' cannot be None",
                            record_id=str(rec_id) if rec_id is not None else None,
                        )
                    )
                continue

            rec_id = rec.get(record_id_field) if record_id_field else None

            if strictly_positive and val <= 0:
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=field_name,
                        value=val,
                        message=f"Value {val} must be strictly positive (> 0)",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )
                continue

            if nonnegative and val < 0:
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=field_name,
                        value=val,
                        message=f"Value {val} must be non-negative (>= 0)",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )
                continue

            if min_value is not None and val < min_value:
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=field_name,
                        value=val,
                        message=f"Value {val} is below minimum allowed value {min_value}",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )

            if max_value is not None and val > max_value:
                errors.append(
                    ValidationErrorDetail(
                        row_index=idx,
                        field=field_name,
                        value=val,
                        message=f"Value {val} exceeds maximum allowed value {max_value}",
                        record_id=str(rec_id) if rec_id is not None else None,
                    )
                )

        return ValidationResult(
            validation_name="numeric_bounds",
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
        )
