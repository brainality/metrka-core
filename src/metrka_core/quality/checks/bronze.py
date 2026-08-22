"""Built-in checks for results produced by Bronze extraction."""

from __future__ import annotations

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult


def bronze_extraction_completed(check_input: QualityCheckInput) -> QualityCheckResult:
    """Check that a requested ZIP extraction completed successfully.

    Intended gate: ``post_bronze`` for checks selected with
    ``applies_to: {extraction_performed: true}``. Required context:
    ``extract_result`` with ``passed``, ``extracted_count``, ``extracted_files``,
    and ``error`` attributes. Optional evidence uses ``safe``,
    ``requested_extract_count``, ``bronze_run_id``, ``bronze_run_path``, and
    ``source_file_name``. The check accepts no built-in parameters.
    """

    context = check_input.context
    extract_result = context["extract_result"]
    passed = bool(extract_result.passed)

    return QualityCheckResult(
        check_type="bronze_extraction_completed",
        status="passed" if passed else "failed",
        expected={"extraction_completed": True, "safe_mode": bool(context.get("safe", True))},
        actual={
            "extraction_completed": passed,
            "extracted_count": extract_result.extracted_count,
            "extracted_files": extract_result.extracted_files,
            "requested_extract_count": context.get("requested_extract_count"),
            "error": extract_result.error,
        },
        result_summary=(
            f"Extracted {extract_result.extracted_count} file(s) to Bronze."
            if passed
            else f"Bronze extraction failed: {extract_result.error}"
        ),
        details={
            "storage_zone": "bronze",
            "bronze_run_id": context.get("bronze_run_id"),
            "bronze_run_path": context.get("bronze_run_path"),
            "source_file_name": context.get("source_file_name"),
        },
        params=dict(check_input.params),
        duration_ms=None,
    )
