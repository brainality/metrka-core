"""PostgreSQL stores for pipeline observability."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from metrka_core.metadata.postgres import PostgresSession, to_jsonb
from metrka_core.observability.execution_step_meta import ExecutionStepMeta


class PostgresPipelineRunStore:
    """Persist canonical pipeline-run receipts."""

    def __init__(self, session: PostgresSession) -> None:
        self._session = session

    def start_pipeline_run(
        self,
        *,
        pipeline_run_id: str,
        workspace_name: str,
        config_name: str,
        code_provenance: dict[str, object],
        started_at: datetime,
    ) -> None:
        if started_at.utcoffset() is None:
            raise ValueError("Pipeline run started_at must be timezone-aware")

        with self._session.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO logs.pipeline_runs (
                    pipeline_run_id,
                    workspace_name,
                    config_name,
                    started_at,
                    status,
                    code_provenance
                )
                VALUES (%s, %s, %s, %s, 'running', %s)
                """,
                (
                    pipeline_run_id,
                    workspace_name,
                    config_name,
                    started_at,
                    to_jsonb(code_provenance),
                ),
            )

    def finish_pipeline_run(
        self,
        *,
        pipeline_run_id: str,
        status: str,
        finished_at: datetime,
        error: dict[str, object] | None = None,
    ) -> None:
        if status not in {"success", "failed"}:
            raise ValueError("Pipeline run status must be 'success' or 'failed'")

        if finished_at.utcoffset() is None:
            raise ValueError("Pipeline run finished_at must be timezone-aware")

        with self._session.cursor() as cursor:
            cursor.execute(
                """
                UPDATE logs.pipeline_runs
                SET
                    finished_at = %s,
                    status = %s,
                    error = %s
                WHERE pipeline_run_id = %s
                """,
                (finished_at, status, to_jsonb(error), pipeline_run_id),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(f"Pipeline run receipt was not found: {pipeline_run_id}")


class PostgresExecutionLogStore:
    """Persist structured execution events."""

    def __init__(self, session: PostgresSession, *, pipeline_run_id: str) -> None:
        self._session = session
        self._pipeline_run_id = pipeline_run_id

    def insert_execution_log(self, record: dict[str, Any]) -> None:
        """Transform an execution receipt into a relational row."""
        counts = record.get("counts", {})
        raw_meta = record.get("meta")
        if raw_meta is not None and not isinstance(raw_meta, dict):
            raise TypeError("Execution event meta must be a dictionary")
        meta = ExecutionStepMeta.from_mapping(raw_meta)
        error = record.get("error") or {}

        with self._session.cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs.execution_logs (
                    ts,
                    schema_version,
                    dataset,
                    dataset_id,
                    dataset_file_id,
                    source_file_name,
                    original_source_file_name,
                    table_key,
                    bronze_run_id,
                    silver_run_id,
                    silver_build_id,
                    partition_key,
                    partition_value,
                    version_period,
                    layer,
                    step,
                    run_id,
                    step_id,
                    event_type,
                    status,
                    duration_ms,
                    success_count,
                    failed_count,
                    skipped_count,
                    blocked_count,
                    contract_hash,
                    contract_name,
                    contract_path,
                    contract_version,
                    contract_snapshot_yaml_path,
                    contract_snapshot_json_path,
                    input_row_count,
                    output_row_count,
                    input_column_count,
                    output_column_count,
                    input_file_count,
                    output_file_count,
                    input_byte_count,
                    output_byte_count,
                    manifest_path,
                    error_code,
                    error_message,
                    error,
                    meta,
                    pipeline_run_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    record.get("ts"),
                    record.get("schema_version"),
                    record.get("dataset"),
                    meta.dataset_id,
                    meta.dataset_file_id,
                    meta.source_file_name,
                    meta.original_source_file_name,
                    meta.table_key,
                    meta.bronze_run_id,
                    meta.silver_run_id,
                    meta.silver_build_id,
                    meta.partition_key,
                    meta.partition_value,
                    meta.version_period,
                    record.get("layer"),
                    record.get("step"),
                    record.get("run_id"),
                    record.get("step_id"),
                    record.get("event_type"),
                    record.get("status"),
                    record.get("duration_ms"),
                    counts.get("success"),
                    counts.get("failed"),
                    counts.get("skipped"),
                    counts.get("blocked"),
                    meta.contract_hash,
                    meta.contract_name,
                    meta.contract_path,
                    meta.contract_version,
                    meta.contract_snapshot_yaml_path,
                    meta.contract_snapshot_json_path,
                    meta.input_row_count,
                    meta.output_row_count,
                    meta.input_column_count,
                    meta.output_column_count,
                    meta.input_file_count,
                    meta.output_file_count,
                    meta.input_byte_count,
                    meta.output_byte_count,
                    meta.manifest_path,
                    error.get("type"),
                    error.get("message"),
                    to_jsonb(record.get("error")),
                    to_jsonb(meta.to_dict() or None),
                    record.get("pipeline_run_id") or self._pipeline_run_id,
                ),
            )
