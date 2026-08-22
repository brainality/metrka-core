"""Reusable tabular data-quality checks."""

from __future__ import annotations

import time

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult


def has_data_rows(check_input: QualityCheckInput) -> QualityCheckResult:
    """Verify that a loaded Silver table contains enough data rows.

    Supported gates: ``pre_silver`` and ``post_silver``. Required context:
    ``table``. Optional evidence uses ``table_key`` and ``source_file_name``.
    Parameter ``min_rows`` defaults to 1 and must be non-negative.
    """

    started = time.perf_counter()
    context = check_input.context

    table = context["table"]
    min_rows = int(check_input.params.get("min_rows", 1))

    if min_rows < 0:
        raise ValueError("min_rows must be greater than or equal to 0")

    row_count = len(table)
    passed = row_count >= min_rows

    return QualityCheckResult(
        check_type="has_data_rows",
        status="passed" if passed else "failed",
        expected={"min_rows": min_rows},
        actual={"row_count": row_count},
        result_summary=(
            f"Table contains {row_count} data row(s)."
            if passed
            else (f"Table contains {row_count} row(s), below the required minimum {min_rows}.")
        ),
        details={
            "quality_gate": check_input.quality_gate.value,
            "table_key": context.get("table_key"),
            "source_file_name": context.get("source_file_name"),
        },
        params={"min_rows": min_rows},
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def expected_columns_present(check_input: QualityCheckInput) -> QualityCheckResult:
    """Verify a Silver table against the gate's expected column set.

    Supported gates: ``pre_silver`` and ``post_silver``. Required context:
    ``table``, a non-empty ``expected_columns`` list, and boolean
    ``allow_extra_columns``. The pipeline sets the boolean to ``True`` before
    transformation and ``False`` after transformation. These values are
    runtime facts rather than declarative check parameters.
    """

    started = time.perf_counter()
    context = check_input.context

    table = context["table"]

    if "expected_columns" not in context:
        raise KeyError("expected_columns_present requires 'expected_columns' in the gate context")

    expected_columns_value = context["expected_columns"]

    if not isinstance(expected_columns_value, list):
        raise TypeError("expected_columns_present requires 'expected_columns' to be a list")

    if not expected_columns_value:
        raise ValueError("expected_columns_present requires a non-empty expected column list")

    expected_columns = [str(column) for column in expected_columns_value]
    actual_columns = [str(column) for column in table.columns]

    if "allow_extra_columns" not in context:
        raise KeyError(
            "expected_columns_present requires 'allow_extra_columns' in the gate context"
        )

    allow_extra_columns = context["allow_extra_columns"]

    if not isinstance(allow_extra_columns, bool):
        raise TypeError("expected_columns_present requires 'allow_extra_columns' to be a boolean")

    missing_columns = sorted(set(expected_columns) - set(actual_columns))
    unexpected_columns = sorted(set(actual_columns) - set(expected_columns))

    passed = not missing_columns and (allow_extra_columns or not unexpected_columns)

    return QualityCheckResult(
        check_type="expected_columns_present",
        status="passed" if passed else "failed",
        expected={"columns": expected_columns, "allow_extra_columns": allow_extra_columns},
        actual={
            "columns": actual_columns,
            "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
        },
        result_summary=(
            "All expected columns are present."
            if passed
            else ("Expected columns are missing or unexpected columns are not allowed.")
        ),
        details={
            "quality_gate": check_input.quality_gate.value,
            "table_key": context.get("table_key"),
            "source_file_name": context.get("source_file_name"),
        },
        params=dict(check_input.params),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
