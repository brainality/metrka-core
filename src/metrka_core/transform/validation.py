"""
Validate Silver YAML contracts before they reach pipeline.

Module checks that contract files are parseable, structurally complete
and internally consistent so schema mistakes fail fast.
"""

from __future__ import annotations

import collections
import logging
from pathlib import Path
from typing import Any

import yaml

from metrka_core.transform.cast_types import SILVER_CAST_TYPE_NAMES, is_date_like_cast_type
from metrka_core.transform.ops.casting import parse_decimal_cast_type

logger = logging.getLogger(__name__)


ALLOWED_COLUMNS_RULE_KEYS = {
    "rename_to",
    "cast_to",
    "format_in",
    "case",
    "normalize_values",
    "meta",
}

ALLOWED_CASE_TYPES = {"upper", "lower", "title"}


class ContractValidationError(ValueError):
    """Raised when a Silver contract file is not safe to execute."""


def validate_contract_file(path: Path) -> dict[str, Any]:
    """
    Validation order:
    1. YAML loads
    2. every table has columns
    3. every column has rename_to and cast_to
    4. no duplicate renamed columns per table
    5. canonical_order exactly matches final renamed columns
    6. supported rule keys only
    7. normalize_values rules are structurally valid and carry non-empty reasons
    8. supported cast types only

    Returns parsed YAML mapping if valid.
    Raises ContractValidationError if invalid.

    """
    logger.info("Validating Silver contract: %s", path)
    data = _validate_contract_loads(path)
    tables = _validate_tables_exist(data, path)

    for table_name, table_cfg in tables.items():
        logger.debug("Validating Silver contract table: %s", table_name)
        columns = _validate_table_has_columns(table_name, table_cfg)
        renamed_columns = _validate_columns_have_required_fields(table_name, columns)
        _validate_no_duplicate_renamed_columns(table_name, renamed_columns)
        _validate_canonical_order_matches(table_name, table_cfg, renamed_columns)
        _validate_supported_rule_keys(table_name, columns)
        _validate_normalize_values_rules(table_name, columns)
        _validate_supported_cast_types(table_name, columns)

    logger.info("Silver contract validation passed: %s tables=%d", path, len(tables))

    return data


def _validate_contract_loads(path: Path) -> dict[str, Any]:
    """Load YAML and guard against missing files, parse errors and non-mapping roots."""
    if not path.exists():
        raise ContractValidationError(f"Contract file does not exist: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ContractValidationError(f"{path}: YAML parse error: {e}") from e

    if not isinstance(data, dict):
        raise ContractValidationError(f"{path}: top-level YAML must be a mapping")
    return data


def _validate_tables_exist(data: dict[str, Any], path: Path) -> dict[str, Any]:
    """Require a non-empty tables block so the contract has executable table definitions."""
    tables = data.get("tables")

    if not isinstance(tables, dict) or not tables:
        raise ContractValidationError(f"{path}: missing or empty 'tables' mapping")
    return tables


def _validate_table_has_columns(table_name: str, table_cfg: Any) -> dict[str, Any]:
    """Require each table to define columns so schema transformation has rules to apply."""
    if not isinstance(table_cfg, dict):
        raise ContractValidationError(f"{table_name}: table config must be a mapping")

    columns = table_cfg.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ContractValidationError(f"{table_name}: missing or empty 'columns' mapping")

    return columns


def _validate_columns_have_required_fields(table_name: str, columns: dict[str, Any]) -> list[str]:
    """Require every source column rule to define rename_to and cast_to."""

    renamed_columns: list[str] = []

    for source_col, rule in columns.items():
        if not isinstance(rule, dict):
            raise ContractValidationError(
                f"{table_name}.{source_col}: column rule must be a mapping"
            )

        rename_to = rule.get("rename_to")
        cast_to = rule.get("cast_to")

        if not isinstance(rename_to, str) or not rename_to.strip():
            raise ContractValidationError(
                f"{table_name}.{source_col}: missing or invalid 'rename_to'"
            )

        if not isinstance(cast_to, str) or not cast_to.strip():
            raise ContractValidationError(
                f"{table_name}.{source_col}: missing or invalid 'cast_to'"
            )

        renamed_columns.append(rename_to)
    return renamed_columns


def _validate_no_duplicate_renamed_columns(table_name: str, rename_columns: list[str]) -> None:
    """Reject duplicate rename_to targets that would overwrite columns after renaming."""
    counts = collections.Counter(rename_columns)
    duplicates = sorted([name for name, count in counts.items() if count > 1])
    if duplicates:
        raise ContractValidationError(
            f"{table_name}: duplicate renamed columns found: {duplicates}"
        )


def _validate_canonical_order_matches(
    table_name: str, table_cfg: dict[str, Any], renamed_columns: list[str]
) -> None:
    """Ensure canonical_order exactly matches final renamed columns for the table."""
    canonical_order = table_cfg.get("canonical_order")

    if canonical_order is None:
        raise ContractValidationError(f"{table_name} is missing canonical_order")

    if not isinstance(canonical_order, list):
        raise ContractValidationError(f"{table_name}: 'canonical_order' must be a list")
    if not all(isinstance(x, str) and x.strip() for x in canonical_order):
        raise ContractValidationError(
            f"{table_name}: 'canonical_order' must contain only non-empty strings"
        )
    counts = collections.Counter(canonical_order)
    duplicate_order = sorted([name for name, count in counts.items() if count > 1])
    if duplicate_order:
        raise ContractValidationError(
            f"{table_name}: duplicate columns in canonical_order: {duplicate_order}"
        )
    renamed_set = set(renamed_columns)
    canonical_set = set(canonical_order)

    missing_from_order = sorted(renamed_set - canonical_set)
    unknown_in_order = sorted(canonical_set - renamed_set)

    if missing_from_order:
        raise ContractValidationError(
            f"{table_name}: canonical_order is missing renamed columns: {missing_from_order}"
        )
    if unknown_in_order:
        raise ContractValidationError(
            f"{table_name}: canonical_order contains unknown columns: {unknown_in_order}"
        )


def _validate_supported_rule_keys(table_name: str, columns: dict[str, Any]) -> None:
    """Reject unsupported column rule keys and unsupported case normalization values."""
    for source_col, rule in columns.items():
        unknown_keys = sorted(set(rule.keys()) - ALLOWED_COLUMNS_RULE_KEYS)
        if unknown_keys:
            raise ContractValidationError(
                f"{table_name}.{source_col}: unsupported rule keys: {unknown_keys}"
            )

        if "case" in rule and rule["case"] not in ALLOWED_CASE_TYPES:
            raise ContractValidationError(
                f"{table_name}.{source_col}: unsupported case '{rule['case']}'. Allowed: {ALLOWED_CASE_TYPES} "
            )


def _validate_normalize_values_rules(table_name: str, columns: dict[str, Any]) -> None:
    """Validate explicit before-to-after value mappings."""

    supported_value_types = (str, int, float, bool)

    final_column_names = {
        str(column_rule.get("rename_to", source_column))
        for source_column, column_rule in columns.items()
        if isinstance(column_rule, dict)
    }

    for source_column, column_rule in columns.items():
        if "normalize_values" not in column_rule:
            continue

        normalize_config = column_rule["normalize_values"]

        if not isinstance(normalize_config, dict):
            raise ContractValidationError(
                f"{table_name}.{source_column}: normalize_values must be a mapping"
            )

        unknown_config_keys = sorted(set(normalize_config) - {"reason", "mappings"})

        if unknown_config_keys:
            raise ContractValidationError(
                f"{table_name}.{source_column}: "
                "unsupported normalize_values keys: "
                f"{unknown_config_keys}"
            )

        default_reason = normalize_config.get("reason")

        if not isinstance(default_reason, str) or not default_reason.strip():
            raise ContractValidationError(
                f"{table_name}.{source_column}: "
                "normalize_values.reason is required and "
                "must be a non-empty string"
            )

        normalize_rules = normalize_config.get("mappings")

        if not isinstance(normalize_rules, dict) or not normalize_rules:
            raise ContractValidationError(
                f"{table_name}.{source_column}: "
                "normalize_values.mappings must be a "
                "non-empty mapping"
            )

        for before_value, replacement_rule in normalize_rules.items():
            if not isinstance(before_value, supported_value_types):
                raise ContractValidationError(
                    f"{table_name}.{source_column}: "
                    "normalize_values source values must "
                    "be scalar values"
                )

            if not isinstance(replacement_rule, dict):
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: replacement rule "
                    "must be a mapping"
                )

            unknown_keys = sorted(
                set(replacement_rule)
                - {"replace_with", "record_details", "detail_columns", "reason"}
            )

            if unknown_keys:
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: unsupported "
                    f"replacement keys: {unknown_keys}"
                )

            if "replace_with" not in replacement_rule:
                raise ContractValidationError(
                    f"{table_name}.{source_column}.{before_value}: missing replace_with"
                )

            reason = replacement_rule.get("reason", default_reason)

            if not isinstance(reason, str) or not reason.strip():
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: reason is required and "
                    "must be a non-empty string"
                )

            record_details = replacement_rule.get("record_details", False)

            if not isinstance(record_details, bool):
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: record_details must "
                    "be true or false"
                )

            detail_columns = replacement_rule.get("detail_columns", [])

            if not isinstance(detail_columns, list) or any(
                not isinstance(column_name, str) or not column_name.strip()
                for column_name in detail_columns
            ):
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: detail_columns must "
                    "be a list of non-empty strings"
                )

            if len(detail_columns) != len(set(detail_columns)):
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: detail_columns must "
                    "not contain duplicates"
                )

            if detail_columns and not record_details:
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: detail_columns requires "
                    "record_details: true"
                )

            unknown_detail_columns = sorted(set(detail_columns) - final_column_names)

            if unknown_detail_columns:
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: unknown final "
                    "detail_columns: "
                    f"{unknown_detail_columns}"
                )

            after_value = replacement_rule["replace_with"]

            if not isinstance(after_value, supported_value_types):
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: replace_with must "
                    "be a scalar value"
                )

            if before_value == after_value:
                raise ContractValidationError(
                    f"{table_name}.{source_column}."
                    f"{before_value}: normalize_values "
                    "must change the value"
                )


def _validate_supported_cast_types(table_name: str, columns: dict[str, Any]) -> None:
    """Validate simple and parameterized Silver cast types."""
    for source_col, rule in columns.items():
        cast_to = rule["cast_to"]

        is_simple_type = cast_to in SILVER_CAST_TYPE_NAMES
        is_decimal_type = parse_decimal_cast_type(cast_to) is not None

        if not is_simple_type and not is_decimal_type:
            raise ContractValidationError(
                f"{table_name}.{source_col}: unsupported cast_to {cast_to!r} "
            )

        format_in = rule.get("format_in")

        if is_date_like_cast_type(cast_to) and (
            not isinstance(format_in, str) or not format_in.strip()
        ):
            raise ContractValidationError(
                f"{table_name}.{source_col}: 'cast_to' requires a non-empty string 'format_in' rule"
            )
