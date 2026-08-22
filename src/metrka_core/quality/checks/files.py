"""Reusable filesystem quality checks."""

from __future__ import annotations

import time
from pathlib import Path

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult


def output_files_created(check_input: QualityCheckInput) -> QualityCheckResult:
    """Verify that a gate produced enough non-empty output files.

    Supported gates: ``post_bronze`` and ``post_silver``. Runtime context uses
    ``output_files`` and optional ``output_required`` (default ``True``). When
    output is not required the check returns ``SKIPPED``. Parameters
    ``min_files`` and ``min_file_bytes`` both default to 1 and must be
    non-negative.
    """

    started = time.perf_counter()
    context = check_input.context

    output_required = bool(context.get("output_required", True))
    min_files = int(check_input.params.get("min_files", 1))
    min_file_bytes = int(check_input.params.get("min_file_bytes", 1))

    if min_files < 0:
        raise ValueError("min_files must be greater than or equal to 0")

    if min_file_bytes < 0:
        raise ValueError("min_file_bytes must be greater than or equal to 0")

    raw_output_files = context.get("output_files") or []

    output_files = [value if isinstance(value, Path) else Path(value) for value in raw_output_files]

    details = {
        "storage_zone": context.get("storage_zone"),
        "bronze_run_id": context.get("bronze_run_id"),
        "bronze_run_path": context.get("bronze_run_path"),
        "output_required": output_required,
    }

    if not output_required:
        return QualityCheckResult(
            check_type="output_files_created",
            status="skipped",
            expected={"output_required": False},
            actual={"output_file_count": 0, "output_files": []},
            result_summary=("Output validation skipped because no new Bronze output was required."),
            details=details,
            params={"min_files": min_files, "min_file_bytes": min_file_bytes},
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    missing_files = [str(path) for path in output_files if not path.is_file()]

    undersized_files = [
        str(path)
        for path in output_files
        if path.is_file() and path.stat().st_size < min_file_bytes
    ]

    passed = len(output_files) >= min_files and not missing_files and not undersized_files

    return QualityCheckResult(
        check_type="output_files_created",
        status="passed" if passed else "failed",
        expected={
            "min_files": min_files,
            "min_file_bytes": min_file_bytes,
            "all_files_exist": True,
        },
        actual={
            "output_file_count": len(output_files),
            "output_files": [str(path) for path in output_files],
            "missing_files": missing_files,
            "undersized_files": undersized_files,
        },
        result_summary=(
            f"Created {len(output_files)} valid output file(s)."
            if passed
            else ("Bronze output files are missing, empty, or fewer than expected.")
        ),
        details=details,
        params={"min_files": min_files, "min_file_bytes": min_file_bytes},
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
