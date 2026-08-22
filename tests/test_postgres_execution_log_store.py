"""Tests for the relational execution-log metadata mapping."""

from __future__ import annotations

from unittest.mock import MagicMock

from metrka_core.observability.execution_step_meta import ExecutionStepMeta
from metrka_core.observability.postgres_stores import PostgresExecutionLogStore


def test_dataset_file_identity_reaches_its_queryable_column() -> None:
    session = MagicMock()
    cursor = session.cursor.return_value.__enter__.return_value
    store = PostgresExecutionLogStore(session, pipeline_run_id="pipeline-1")

    store.insert_execution_log(
        {
            "ts": "2026-08-16T12:00:00+00:00",
            "schema_version": 1,
            "dataset": "adult-lead",
            "layer": "bronze",
            "step": "ingest_and_stage",
            "run_id": "bronze-1",
            "step_id": "step-1",
            "event_type": "step_started",
            "meta": ExecutionStepMeta(
                dataset_id="wi_dhs_adult_lead.county", dataset_file_id="file-123"
            ).to_dict(),
        }
    )

    parameters = cursor.execute.call_args.args[1]

    assert parameters[3] == "wi_dhs_adult_lead.county"
    assert parameters[4] == "file-123"
