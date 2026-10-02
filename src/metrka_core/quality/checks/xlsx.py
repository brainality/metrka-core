"""Built-in integrity check for landed XLSX packages."""

from __future__ import annotations

from pathlib import Path

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult
from metrka_core.validation.preflight.xlsx_verify import verify_single_xlsx


def xlsx_package_integrity(check_input: QualityCheckInput) -> QualityCheckResult:
    """Verify the physical integrity of a landed XLSX package."""

    context = check_input.context
    landed_file: Path = context["landed_file"]

    if landed_file.suffix.lower() != ".xlsx":
        return QualityCheckResult(
            check_type="xlsx_package_integrity",
            status="skipped",
            expected={"valid_xlsx_package": True},
            actual={
                "file_name": landed_file.name,
                "valid_xlsx_package": None,
                "skipped_reason": "not_xlsx",
            },
            result_summary=("XLSX package check skipped because the source file is not XLSX."),
            details={
                "storage_zone": context.get("storage_zone", "landing"),
                "landing_path": context.get("landing_path"),
                "source_file_name": landed_file.name,
            },
            params={},
            duration_ms=None,
        )

    verification = verify_single_xlsx(landed_file)

    return QualityCheckResult(
        check_type="xlsx_package_integrity",
        status="passed" if verification.passed else "failed",
        expected={
            "valid_xlsx_package": True,
            "required_members_present": True,
            "min_worksheets": 1,
        },
        actual={
            "file_name": landed_file.name,
            "valid_xlsx_package": verification.passed,
            "zip_container": verification.is_zipfile,
            "crc_ok": verification.crc_ok,
            "crc_bad_member": verification.crc_bad_member,
            "missing_members": list(verification.missing_members),
            "worksheet_count": verification.worksheet_count,
            "error": verification.error,
        },
        result_summary=(
            "XLSX package passed physical integrity verification."
            if verification.passed
            else f"XLSX package failed physical integrity verification: {verification.error}"
        ),
        details={
            "storage_zone": context.get("storage_zone", "landing"),
            "landing_path": context.get("landing_path"),
            "source_file_name": landed_file.name,
        },
        params={},
        duration_ms=None,
    )
