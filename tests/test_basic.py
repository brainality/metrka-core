from __future__ import annotations

from pathlib import Path

from metrka_core.quality.checks.basic import file_size_min
from metrka_core.quality.models import QualityCheckInput, QualityGate


def _input(path: Path, *, min_bytes: int) -> QualityCheckInput:
    return QualityCheckInput(
        context={
            "landed_file": path,
            "storage_zone": "landing",
            "landing_path": f"data/files/bronze/landing/{path.name}",
        },
        params={"min_bytes": min_bytes},
        check_id="file-size",
        quality_gate=QualityGate.PRE_BRONZE,
        applies_to={},
    )


def test_file_size_min_passes_without_exposing_absolute_path(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    source.write_bytes(b"abc")

    result = file_size_min(_input(source, min_bytes=1))

    assert result.status == "passed"
    assert result.expected == {"min_bytes": 1}
    assert result.actual == {
        "file_name": "source.zip",
        "exists": True,
        "is_file": True,
        "file_size_bytes": 3,
    }
    assert str(tmp_path) not in str(result.actual)


def test_file_size_min_fails_when_file_is_too_small(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    source.write_bytes(b"abc")

    result = file_size_min(_input(source, min_bytes=10))

    assert result.status == "failed"
    assert result.actual["file_size_bytes"] == 3
    assert "below minimum" in result.result_summary


def test_file_size_min_fails_when_file_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "missing.zip"

    result = file_size_min(_input(source, min_bytes=1))

    assert result.status == "failed"
    assert result.actual["exists"] is False
    assert result.actual["file_size_bytes"] is None
    assert "does not exist" in result.result_summary
