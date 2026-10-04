from pathlib import Path

import pandas as pd

from metrka_core.quality.checks.xlsx import xlsx_has_data_rows
from metrka_core.quality.models import QualityCheckInput, QualityGate
from metrka_core.quality.registry import create_default_quality_registry


def _check_input(path: Path, *, min_rows: int = 1) -> QualityCheckInput:
    return QualityCheckInput(
        context={
            "landed_file": path,
            "storage_zone": "landing",
            "landing_path": f"files/bronze/landing/{path.name}",
            "xlsx_sheet_name": 0,
            "xlsx_header_row": 0,
        },
        params={"min_rows": min_rows},
        check_id="xlsx-has-data-rows",
        quality_gate=QualityGate.PRE_BRONZE,
        applies_to={},
    )


def test_xlsx_with_data_rows_passes(tmp_path: Path) -> None:
    path = tmp_path / "with-data.xlsx"

    pd.DataFrame([{"County": "Florida", "Count": 10}]).to_excel(path, index=False)

    result = xlsx_has_data_rows(_check_input(path))

    assert result.status == "passed"
    assert result.expected == {"min_rows": 1}
    assert result.actual["file_name"] == path.name
    assert result.actual["row_count"] == 1


def test_header_only_xlsx_fails(tmp_path: Path) -> None:
    path = tmp_path / "header-only.xlsx"

    pd.DataFrame(columns=["County", "Count"]).to_excel(path, index=False)

    result = xlsx_has_data_rows(_check_input(path))

    assert result.status == "failed"
    assert result.expected == {"min_rows": 1}
    assert result.actual["file_name"] == path.name
    assert result.actual["row_count"] == 0


def test_xlsx_has_data_rows_is_registered() -> None:
    registry = create_default_quality_registry()

    assert registry.resolve("xlsx_has_data_rows") is xlsx_has_data_rows
