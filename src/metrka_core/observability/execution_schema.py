"""Validation helpers for execution log events."""

from __future__ import annotations

from typing import Any, Literal

from metrka_core.observability.execution_step_meta import ExecutionStepMeta

type StepStatus = Literal["success", "failed", "skipped", "blocked", "interrupted"]

VALID_EVENT_TYPES = frozenset({"step_started", "step_finished"})
VALID_STEP_STATUS = frozenset({"success", "failed", "skipped", "blocked", "interrupted"})

BASE_REQUIRED = frozenset(
    {"ts", "schema_version", "dataset", "layer", "step", "run_id", "step_id", "event_type"}
)

BASE_ALLOWED = BASE_REQUIRED | frozenset({"meta"})

STEP_FINISHED_FIELDS = frozenset({"status", "duration_ms", "counts"})
STEP_FINISHED_ALLOWED_EXTRA = STEP_FINISHED_FIELDS | frozenset({"error"})


def validate_execution_event(record: dict[str, Any]) -> None:
    """Validate one execution event record."""
    if not isinstance(record, dict):
        raise ValueError("execution event must be a dict")

    event_type = record.get("event_type")

    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unknown execution event_type: {event_type}")

    required = (
        BASE_REQUIRED | STEP_FINISHED_FIELDS if event_type == "step_finished" else BASE_REQUIRED
    )
    allowed = (
        BASE_ALLOWED | STEP_FINISHED_ALLOWED_EXTRA
        if event_type == "step_finished"
        else BASE_ALLOWED
    )

    missing = [key for key in required if key not in record]

    if missing:
        raise ValueError(f"{event_type}: missing required fields: {missing}")

    unknown = [key for key in record if key not in allowed]

    if unknown:
        raise ValueError(
            f"{event_type}: unknown top-level fields: {unknown}. "
            "Put optional extras under record['meta']."
        )

    meta = record.get("meta")

    if meta is not None and not isinstance(meta, dict):
        raise ValueError(f"{event_type}: meta must be a dict when provided")

    if isinstance(meta, dict):
        ExecutionStepMeta.from_mapping(meta)

    if event_type == "step_finished":
        _validate_step_finished(record)


def _validate_step_finished(record: dict[str, Any]) -> None:
    status = record.get("status")

    if status not in VALID_STEP_STATUS:
        raise ValueError(
            "step_finished: status must be one of success|failed|skipped|blocked|interrupted"
        )

    duration_ms = record.get("duration_ms")

    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms < 0:
        raise ValueError("step_finished: duration_ms must be a non-negative int")

    counts = record.get("counts")

    if not isinstance(counts, dict):
        raise ValueError("step_finished: counts must be a dict")

    required_counts = {"success", "failed", "skipped", "blocked"}
    missing_counts = required_counts - counts.keys()

    if missing_counts:
        raise ValueError(f"step_finished: counts missing keys: {sorted(missing_counts)}")

    for key, value in counts.items():
        if (
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError("step_finished: counts must be dict[str, non-negative int]")
