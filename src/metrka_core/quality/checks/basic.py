"""Built-in checks for landed-file size and recorded digest metadata."""

from __future__ import annotations

import time
from pathlib import Path

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult


def file_size_min(check_input: QualityCheckInput) -> QualityCheckResult:
    """Check that a landed file exists and meets the configured minimum size.

    Intended gate: ``pre_bronze``. Required context: ``landed_file`` as a
    ``Path``. Optional context used for evidence: ``storage_zone`` and
    ``landing_path``. Parameter ``min_bytes`` defaults to 1 and must be
    non-negative.
    """

    started = time.perf_counter()
    context = check_input.context

    path: Path = context["landed_file"]
    min_bytes = int(check_input.params.get("min_bytes", 1))

    if min_bytes < 0:
        raise ValueError("min_bytes must be greater than or equal to 0")

    file_name = path.name

    details = {
        "storage_zone": context.get("storage_zone", "landing"),
        "landing_path": context.get("landing_path"),
        "source_file_name": file_name,
    }

    if not path.exists():
        return QualityCheckResult(
            check_type="file_size_min",
            status="failed",
            expected={"min_bytes": min_bytes},
            actual={"file_name": file_name, "exists": False, "file_size_bytes": None},
            result_summary=f"File does not exist: {file_name}",
            details=details,
            params={"min_bytes": min_bytes},
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    if not path.is_file():
        return QualityCheckResult(
            check_type="file_size_min",
            status="failed",
            expected={"min_bytes": min_bytes},
            actual={
                "file_name": file_name,
                "exists": True,
                "is_file": False,
                "file_size_bytes": None,
            },
            result_summary=f"Path exists but is not a file: {file_name}",
            details=details,
            params={"min_bytes": min_bytes},
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    file_size = path.stat().st_size
    passed = file_size >= min_bytes

    return QualityCheckResult(
        check_type="file_size_min",
        status="passed" if passed else "failed",
        expected={"min_bytes": min_bytes},
        actual={
            "file_name": file_name,
            "exists": True,
            "is_file": True,
            "file_size_bytes": file_size,
        },
        result_summary=(
            f"File size {file_size} bytes is >= minimum {min_bytes} bytes."
            if passed
            else f"File size {file_size} bytes is below minimum {min_bytes} bytes."
        ),
        details=details,
        params={"min_bytes": min_bytes},
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def sha256_recorded(check_input: QualityCheckInput) -> QualityCheckResult:
    """Check that landing recorded a 64-character SHA-256 value.

    Intended gate: ``pre_bronze``. Required context: ``landed_file``. The
    optional ``content_hash`` runtime fact is reported as failed when absent or
    malformed. This check verifies recorded metadata shape; it does not reread
    the file. It accepts no declarative parameters.
    """

    context = check_input.context
    content_hash = context.get("content_hash")
    landed_file: Path = context["landed_file"]

    passed = bool(content_hash) and len(str(content_hash)) == 64

    return QualityCheckResult(
        check_type="sha256_recorded",
        status="passed" if passed else "failed",
        expected={"algorithm": "sha256", "hex_length": 64, "required": True},
        actual={
            "file_name": landed_file.name,
            "algorithm": "sha256",
            "hash_present": bool(content_hash),
            "hash_hex_length": len(str(content_hash)) if content_hash else 0,
            "sha256": content_hash,
        },
        result_summary=(
            "SHA-256 hash was computed and recorded."
            if passed
            else "SHA-256 hash was not computed correctly."
        ),
        details={
            "storage_zone": context.get("storage_zone", "landing"),
            "landing_path": context.get("landing_path"),
            "source_file_name": landed_file.name,
        },
        params={"algorithm": "sha256"},
        duration_ms=None,
    )
