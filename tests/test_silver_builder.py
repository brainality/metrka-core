from __future__ import annotations

from datetime import UTC, date, datetime
from itertools import count
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from metrka_core.pipeline.silver.silver_builder import build_silver_table
from metrka_core.pipeline.silver.version_period import VersionPeriod
from metrka_core.quality.models import QualityCheckSpec, QualityConfig, QualityGate, QualitySeverity
from metrka_core.quality.registry import create_default_quality_registry
from metrka_core.storage.silver_store import LocalSilverArtifactStore

SILVER_PROCESSED_AT = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def _silver_store(tmp_path: Path) -> LocalSilverArtifactStore:
    return LocalSilverArtifactStore(
        workspace_root=tmp_path,
        silver_root=tmp_path / "data" / "files" / "silver",
        current_root=tmp_path / "data" / "current",
    )


def _contract(tmp_path: Path) -> Path:
    contract = tmp_path / "conf" / "contract.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        """
tables:
  people:
    columns:
      id:
        rename_to: id
        cast_to: string
      name:
        rename_to: name
        cast_to: string
    canonical_order:
      - id
      - name
""".lstrip(),
        encoding="utf-8",
    )
    return contract


def _quality_config() -> QualityConfig:
    return QualityConfig(
        version=1,
        checks=(
            QualityCheckSpec(
                check_id="test-pre-silver-rows",
                check_type="has_data_rows",
                gate=QualityGate.PRE_SILVER,
                severity=QualitySeverity.BLOCKING,
                params={"min_rows": 1},
            ),
            QualityCheckSpec(
                check_id="test-post-silver-rows",
                check_type="has_data_rows",
                gate=QualityGate.POST_SILVER,
                severity=QualitySeverity.BLOCKING,
                params={"min_rows": 1},
            ),
        ),
    )


def _build(
    *,
    tmp_path: Path,
    source: Path,
    input_format: str = "csv",
    transformation_impact_store: MagicMock | None = None,
    transformation_impact_ids: MagicMock | None = None,
):
    resolved_impact_store = (
        transformation_impact_store if transformation_impact_store is not None else MagicMock()
    )

    if transformation_impact_ids is None:
        resolved_impact_ids = MagicMock()
        impact_number = count(1)

        resolved_impact_ids.new_transformation_impact_id.side_effect = lambda: (
            f"impact-test-{next(impact_number)}"
        )
    else:
        resolved_impact_ids = transformation_impact_ids

    return build_silver_table(
        dataset_name="people",
        silver_store=_silver_store(tmp_path),
        dataset_id="people.dataset",
        bronze_file_id="bronze-file-1",
        bronze_run_id="bronze-run-1",
        silver_build_id="silver-build-1",
        version_period=VersionPeriod(value=date(2025, 1, 1), grain="year", source="column:year"),
        partition_key="version_period",
        partition_value="2025",
        source_file_name=source.name,
        bronze_ingested_at=datetime(2026, 8, 13, tzinfo=UTC),
        silver_processed_at=SILVER_PROCESSED_AT,
        input_file_path=source,
        cfg_path=_contract(tmp_path),
        table_key="people",
        execution_log_store=MagicMock(),
        quality_store=MagicMock(),
        transformation_impact_store=resolved_impact_store,
        transformation_impact_ids=resolved_impact_ids,
        run_id="silver-run-1",
        pipeline_run_id="pipeline-1",
        quality_config=_quality_config(),
        quality_registry=create_default_quality_registry(),
        input_format=input_format,
        output_formats="csv",
    )


def test_builder_writes_data_preview_and_business_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "people.csv"
    source.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    result = _build(tmp_path=tmp_path, source=source)

    data_path = next(path for path in result.staged_paths if path.suffix == ".csv")
    preview_path = next(path for path in result.staged_paths if path.suffix == ".json")
    output = pd.read_csv(data_path, dtype=str)

    assert data_path.is_file()
    assert preview_path.is_file()
    assert result.fingerprint.table_key == "people"
    assert result.fingerprint.row_count == 2
    assert result.fingerprint.column_count == 2
    assert output["dataset_id"].unique().tolist() == ["people.dataset"]


def test_builder_rejects_unsupported_input_format(tmp_path: Path) -> None:
    source = tmp_path / "people.json"
    source.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported input_format"):
        _build(tmp_path=tmp_path, source=source, input_format="json")


def test_builder_assigns_explicit_identity_and_time_to_impacts(tmp_path: Path) -> None:
    source = tmp_path / "people.csv"
    source.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    impact_store = MagicMock()
    impact_ids = MagicMock()
    impact_number = count(1)

    impact_ids.new_transformation_impact_id.side_effect = lambda: (
        f"impact-fixed-{next(impact_number)}"
    )

    _build(
        tmp_path=tmp_path,
        source=source,
        transformation_impact_store=impact_store,
        transformation_impact_ids=impact_ids,
    )

    impact_store.insert_many.assert_called_once()

    impacts = impact_store.insert_many.call_args.args[0]

    assert impacts
    assert all(impact.recorded_at == SILVER_PROCESSED_AT for impact in impacts)
    assert all(impact.transformation_impact_id.startswith("impact-fixed-") for impact in impacts)
    assert impact_ids.new_transformation_impact_id.call_count == len(impacts)
