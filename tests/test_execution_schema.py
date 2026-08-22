"""Tests for the operational execution-event contract."""

from __future__ import annotations

from typing import Any

import pytest

from metrka_core.observability.execution_schema import validate_execution_event


def base_record(*, event_type: str) -> dict[str, Any]:
    """Return a minimal execution event used by schema tests."""
    return {
        "ts": "2026-03-02T00:00:00Z",
        "schema_version": 1,
        "dataset": "ds_dummy",
        "layer": "none",
        "step": "step_x",
        "run_id": "run_123",
        "step_id": "step_0001",
        "event_type": event_type,
    }


def test_validate_step_started_ok() -> None:
    rec = base_record(event_type="step_started") | {"meta": {"files": 2}}
    validate_execution_event(rec)


def test_step_id_is_required() -> None:
    rec = base_record(event_type="step_started")
    del rec["step_id"]

    with pytest.raises(ValueError, match="missing required fields"):
        validate_execution_event(rec)


@pytest.mark.parametrize("status", ["success", "failed", "skipped", "blocked", "interrupted"])
def test_validate_step_finished_accepts_known_statuses(status: str) -> None:
    rec = base_record(event_type="step_finished") | {
        "status": status,
        "duration_ms": 10,
        "counts": {"success": 2, "failed": 0, "skipped": 0, "blocked": 0},
    }
    validate_execution_event(rec)


def test_step_finished_duration_ms_is_numeric() -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "success",
        "duration_ms": "bananana",
        "counts": {"success": 2, "failed": 0, "skipped": 0, "blocked": 0},
    }
    with pytest.raises(ValueError, match="duration_ms must be a non-negative int"):
        validate_execution_event(rec)


@pytest.mark.parametrize("invalid_duration", [-1, True])
def test_step_finished_duration_rejects_negative_and_boolean(invalid_duration: int) -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "success",
        "duration_ms": invalid_duration,
        "counts": {"success": 2, "failed": 0, "skipped": 0, "blocked": 0},
    }

    with pytest.raises(ValueError, match="duration_ms must be a non-negative int"):
        validate_execution_event(rec)


def test_step_finished_status_is_valid() -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "mystery",
        "duration_ms": 10,
        "counts": {"success": 2, "failed": 0, "skipped": 0, "blocked": 0},
    }
    with pytest.raises(ValueError, match="status must be one of"):
        validate_execution_event(rec)


def test_step_finished_counts_values_are_int() -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "success",
        "duration_ms": 10,
        "counts": {"success": "two", "failed": 0, "skipped": 0, "blocked": 0},
    }

    with pytest.raises(ValueError, match="step_finished: counts must be dict"):
        validate_execution_event(rec)


@pytest.mark.parametrize("invalid_count", [-1, True])
def test_step_finished_counts_reject_negative_and_boolean(invalid_count: int) -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "success",
        "duration_ms": 10,
        "counts": {"success": invalid_count, "failed": 0, "skipped": 0, "blocked": 0},
    }

    with pytest.raises(ValueError, match=r"counts must be dict\[str, non-negative int\]"):
        validate_execution_event(rec)


def test_unknown_top_level_field_rejected() -> None:
    rec = base_record(event_type="step_started") | {"this_is_a_typo": 123}
    with pytest.raises(ValueError, match="unknown top-level fields"):
        validate_execution_event(rec)


def test_unknown_field_allowed_in_meta() -> None:
    rec = base_record(event_type="step_started") | {"meta": {"this_is_a_typo": 123}}
    validate_execution_event(rec)


def test_meta_must_be_dict() -> None:
    rec = base_record(event_type="step_started") | {"meta": "not-a-dict"}
    with pytest.raises(ValueError, match="meta must be a dict"):
        validate_execution_event(rec)


def test_missing_required_field_rejected() -> None:
    rec = base_record(event_type="step_finished")

    with pytest.raises(ValueError, match="missing required fields"):
        validate_execution_event(rec)


def test_unknown_event_type_rejected() -> None:
    rec = base_record(event_type="not_a_real_event")
    with pytest.raises(ValueError, match="unknown execution event_type"):
        validate_execution_event(rec)


def test_step_finished_counts_requires_all_counter_keys() -> None:
    rec = base_record(event_type="step_finished") | {
        "status": "success",
        "duration_ms": 10,
        "counts": {"success": 1},
    }

    with pytest.raises(ValueError, match="counts missing keys"):
        validate_execution_event(rec)
