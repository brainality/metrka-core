from __future__ import annotations

from pathlib import Path

import pytest

from metrka_core.quality.checks.files import output_files_created
from metrka_core.quality.models import QualityCheckInput, QualityGate, QualityOutputFile


def _input(
    output_files: tuple[QualityOutputFile, ...], *, min_file_bytes: int = 1
) -> QualityCheckInput:
    return QualityCheckInput(
        context={"output_required": True, "output_files": output_files, "storage_zone": "bronze"},
        params={"min_files": 1, "min_file_bytes": min_file_bytes},
        check_id="output-files",
        quality_gate=QualityGate.POST_BRONZE,
        applies_to={},
    )


def test_output_files_created_persists_only_workspace_relative_paths(tmp_path: Path) -> None:
    local_path = tmp_path / "data" / "files" / "bronze" / "runs" / "run-1" / "output.csv"
    local_path.parent.mkdir(parents=True)
    local_path.write_bytes(b"id\n1\n")

    relative_path = "data/files/bronze/runs/run-1/output.csv"

    result = output_files_created(
        _input((QualityOutputFile(local_path=local_path, workspace_relative_path=relative_path),))
    )

    assert result.status == "passed"
    assert result.actual == {
        "output_file_count": 1,
        "output_files": [relative_path],
        "missing_files": [],
        "undersized_files": [],
    }
    assert str(tmp_path) not in str(result.actual)


def test_output_files_created_uses_relative_paths_for_failures(tmp_path: Path) -> None:
    missing_local_path = tmp_path / "missing.csv"
    small_local_path = tmp_path / "small.csv"
    small_local_path.write_bytes(b"")

    result = output_files_created(
        _input(
            (
                QualityOutputFile(
                    local_path=missing_local_path,
                    workspace_relative_path=("data/files/bronze/runs/run-1/missing.csv"),
                ),
                QualityOutputFile(
                    local_path=small_local_path,
                    workspace_relative_path=("data/files/bronze/runs/run-1/small.csv"),
                ),
            )
        )
    )

    assert result.status == "failed"
    assert result.actual["output_files"] == [
        "data/files/bronze/runs/run-1/missing.csv",
        "data/files/bronze/runs/run-1/small.csv",
    ]
    assert result.actual["missing_files"] == ["data/files/bronze/runs/run-1/missing.csv"]
    assert result.actual["undersized_files"] == ["data/files/bronze/runs/run-1/small.csv"]
    assert str(tmp_path) not in str(result.actual)


@pytest.mark.parametrize(
    "workspace_relative_path",
    [
        "C:/Users/operator/output.csv",
        "/srv/metrka/output.csv",
        "../output.csv",
        r"data\files\output.csv",
    ],
)
def test_quality_output_file_rejects_nonportable_persisted_paths(
    tmp_path: Path, workspace_relative_path: str
) -> None:
    with pytest.raises(ValueError):
        QualityOutputFile(
            local_path=tmp_path / "output.csv", workspace_relative_path=workspace_relative_path
        )


def test_output_files_created_rejects_untyped_runtime_paths(tmp_path: Path) -> None:
    check_input = QualityCheckInput(
        context={"output_files": [tmp_path / "output.csv"]},
        params={},
        check_id="output-files",
        quality_gate=QualityGate.POST_BRONZE,
        applies_to={},
    )

    with pytest.raises(TypeError, match="QualityOutputFile"):
        output_files_created(check_input)
