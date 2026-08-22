"""Built-in checks for landing payload-fingerprint metadata."""

from __future__ import annotations

from pathlib import Path

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult


def payload_fingerprint_recorded(check_input: QualityCheckInput) -> QualityCheckResult:
    """Check that landing recorded at least one payload fingerprint member.

    Intended gate: ``pre_bronze``. Required context: ``landed_file``. Optional
    ``fingerprint_meta`` defaults to an empty mapping and therefore fails the
    check. ``storage_zone`` and ``landing_path`` are included as evidence. The
    check accepts no declarative parameters.
    """

    context = check_input.context
    fingerprint_meta = context.get("fingerprint_meta") or {}
    landed_file: Path = context["landed_file"]

    fingerprint_count = len(fingerprint_meta)
    passed = fingerprint_count > 0

    return QualityCheckResult(
        check_type="payload_fingerprint_recorded",
        status="passed" if passed else "failed",
        expected={"fingerprint_required": True, "min_member_count": 1},
        actual={
            "file_name": landed_file.name,
            "fingerprint_recorded": passed,
            "member_count": fingerprint_count,
            "members": sorted(fingerprint_meta.keys()),
        },
        result_summary=(
            f"Payload fingerprint recorded for {fingerprint_count} file(s)."
            if passed
            else "Payload fingerprint was not recorded."
        ),
        details={
            "storage_zone": context.get("storage_zone", "landing"),
            "landing_path": context.get("landing_path"),
            "source_file_name": landed_file.name,
        },
        params={},
        duration_ms=None,
    )
