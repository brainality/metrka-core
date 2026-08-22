from __future__ import annotations

from types import SimpleNamespace

from metrka_core.quality.checks.bronze import bronze_extraction_completed
from metrka_core.quality.models import QualityCheckInput, QualityGate


def test_bronze_extraction_completed_records_extracted_files() -> None:
    result = bronze_extraction_completed(
        QualityCheckInput(
            context={
                "extract_result": SimpleNamespace(
                    passed=True,
                    extracted_count=2,
                    extracted_files=["inmates.csv", "releases.csv"],
                    error=None,
                ),
                "requested_extract_count": 2,
                "safe": True,
            },
            params={},
            check_id="bronze-extraction",
            quality_gate=QualityGate.POST_BRONZE,
            applies_to={},
        )
    )

    assert result.actual["extracted_count"] == 2
    assert result.actual["extracted_files"] == ["inmates.csv", "releases.csv"]
