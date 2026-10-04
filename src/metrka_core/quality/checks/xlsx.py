"""Built-in integrity check for landed XLSX packages."""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

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


def xlsx_has_data_rows(check_input: QualityCheckInput) -> QualityCheckResult:
    """Verify that a landed XLSX file contains enough data rows."""

    started = time.perf_counter()
    context = check_input.context
    landed_file: Path = context["landed_file"]

    min_rows = int(check_input.params.get("min_rows", 1))

    if min_rows < 0:
        raise ValueError("min_rows must be greater than or equal to 0")

    sheet_name = context["xlsx_sheet_name"]
    header_row = context["xlsx_header_row"]

    frame = pd.read_excel(landed_file, sheet_name=sheet_name, header=header_row)
    non_empty_rows = frame.dropna(axis="index", how="all")
    row_count = len(non_empty_rows.index)
    passed = row_count >= min_rows

    return QualityCheckResult(
        check_type="xlsx_has_data_rows",
        status="passed" if passed else "failed",
        expected={"min_rows": min_rows},
        actual={
            "file_name": landed_file.name,
            "row_count": row_count,
            "sheet_name": sheet_name,
            "header_row": header_row,
        },
        result_summary=(
            f"XLSX file contains {row_count} data row(s)."
            if passed
            else (
                f"XLSX file contains {row_count} data row(s), "
                f"below the required minimum {min_rows}."
            )
        ),
        details={
            "storage_zone": context.get("storage_zone", "landing"),
            "landing_path": context.get("landing_path"),
            "source_file_name": landed_file.name,
        },
        params={"min_rows": min_rows},
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
