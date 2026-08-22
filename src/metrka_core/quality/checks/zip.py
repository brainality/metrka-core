"""Built-in integrity checks for landed ZIP archives."""

from __future__ import annotations

from pathlib import Path

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult
from metrka_core.validation.preflight.zip_verify import verify_single_zip


def zip_crc_valid(check_input: QualityCheckInput) -> QualityCheckResult:
    """Check that a landed ZIP archive passes member CRC verification.

    Intended gate: ``pre_bronze``. Required context: ``landed_file`` as a
    ``Path``. Non-ZIP inputs return ``SKIPPED`` so selectors can share one
    configuration safely. ``storage_zone`` and ``landing_path`` are included as
    evidence. The check accepts no declarative parameters.
    """

    context = check_input.context
    landed_file: Path = context["landed_file"]

    details = {
        "storage_zone": context.get("storage_zone", "landing"),
        "landing_path": context.get("landing_path"),
        "source_file_name": landed_file.name,
    }

    if landed_file.suffix.lower() != ".zip":
        return QualityCheckResult(
            check_type="zip_crc_valid",
            status="skipped",
            expected={"zip_crc_valid": True},
            actual={
                "file_name": landed_file.name,
                "zip_crc_valid": None,
                "skipped_reason": "not_zip",
            },
            result_summary="ZIP CRC check skipped because source archive is not a ZIP file.",
            details=details,
            params={},
            duration_ms=None,
        )

    verify_result = verify_single_zip(landed_file)

    return QualityCheckResult(
        check_type="zip_crc_valid",
        status="passed" if verify_result.passed else "failed",
        expected={"zip_crc_valid": True},
        actual={
            "file_name": landed_file.name,
            "zip_crc_valid": bool(verify_result.passed),
            "error": verify_result.error,
        },
        result_summary=(
            "ZIP archive passed CRC verification."
            if verify_result.passed
            else f"ZIP archive failed CRC verification: {verify_result.error}"
        ),
        details=details,
        params={},
        duration_ms=None,
    )
