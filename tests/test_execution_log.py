from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from metrka_core.observability.execution_ids import UuidExecutionIdGenerator
from metrka_core.observability.execution_log import ExecutionLog, ExecutionTimer
from metrka_core.observability.execution_step_meta import ExecutionStepMeta


class FixedExecutionIds:
    """Return predictable identifiers for tests."""

    def new_run_id(self, prefix: str) -> str:
        return f"{prefix}_fixed_run"

    def new_step_id(self, prefix: str = "step") -> str:
        return f"{prefix}_fixed_step"


FROZEN_TIME = datetime(2026, 8, 14, 12, 30, 0, 123456, tzinfo=UTC)


class FrozenClock:
    """Return one deterministic UTC timestamp."""

    def now_utc(self) -> datetime:
        return FROZEN_TIME


class SequenceMonotonicClock:
    """Return configured monotonic values."""

    def __init__(self, *values: float) -> None:
        self._values = iter(values)

    def monotonic(self) -> float:
        return next(self._values)


def test_execution_log_uses_injected_identifiers() -> None:
    log = ExecutionLog(
        dataset="adult-lead",
        step="prepare",
        layer="silver",
        store=MagicMock(),
        ids=FixedExecutionIds(),
    )

    assert log.run_id == "silver_fixed_run"
    assert log.step_id == "step_fixed_step"


def test_identifiers_have_requested_prefixes() -> None:
    ids = UuidExecutionIdGenerator()

    assert ids.new_run_id("bronze").startswith("bronze_")
    assert ids.new_step_id().startswith("step_")
    assert ids.new_step_id("load").startswith("load_")


def test_timer_uses_monotonic_clock() -> None:
    clock = SequenceMonotonicClock(100.0, 100.125)

    timer = ExecutionTimer(clock=clock)

    assert timer.ms() == 125


@pytest.mark.parametrize("layer", ["", "Bronze", "gold", "platinum"])
def test_execution_log_rejects_invalid_layer(layer: str) -> None:
    with pytest.raises(ValueError, match="layer must be one of"):
        ExecutionLog(
            dataset="adult-lead",
            step="extract_archive",
            layer=layer,  # type: ignore[arg-type]
            store=MagicMock(),
        )


def test_execution_log_requires_dataset_step_and_store() -> None:
    with pytest.raises(ValueError, match="dataset must not be blank"):
        ExecutionLog(dataset=" ", step="load", store=MagicMock())

    with pytest.raises(ValueError, match="step must not be blank"):
        ExecutionLog(dataset="adult-lead", step=" ", store=MagicMock())

    with pytest.raises(ValueError, match="store is required"):
        ExecutionLog(
            dataset="adult-lead",
            step="load",
            store=None,  # type: ignore[arg-type]
        )


def test_base_record_uses_explicit_dataset_identity() -> None:
    log = ExecutionLog(
        dataset="adult-lead",
        step="extract_archive",
        layer="bronze",
        run_id="run-1",
        step_id="step-1",
        store=MagicMock(),
        clock=FrozenClock(),
    )

    record = log.base_record(
        event_type="step_started", meta=ExecutionStepMeta(extra={"source": "landing"})
    )

    assert record["ts"] == "2026-08-14T12:30:00.123456+00:00"
    assert record["dataset"] == "adult-lead"
    assert record["run_id"] == "run-1"
    assert record["step_id"] == "step-1"
    assert record["meta"] == {"source": "landing"}


def test_step_events_are_validated_and_written(mocker: MockerFixture) -> None:
    store = MagicMock()
    validate = mocker.patch("metrka_core.observability.execution_log.validate_execution_event")
    log = ExecutionLog(
        dataset="adult-lead",
        step="prepare",
        layer="silver",
        run_id="run-1",
        step_id="step-1",
        store=store,
    )

    started = log.step_started(meta=ExecutionStepMeta(table_key="county"))
    finished = log.step_finished(
        status="success",
        duration_ms=15,
        counts={"success": 1, "failed": 0, "skipped": 0, "blocked": 0},
    )

    assert started["event_type"] == "step_started"
    assert finished["event_type"] == "step_finished"
    assert store.insert_execution_log.call_count == 2
    assert validate.call_count == 2


def test_invalid_event_is_never_inserted(mocker: MockerFixture) -> None:
    store = MagicMock()
    validate = mocker.patch(
        "metrka_core.observability.execution_log.validate_execution_event",
        side_effect=ValueError("invalid execution event"),
    )
    log = ExecutionLog(dataset="adult-lead", step="prepare", store=store)
    record = log.base_record(event_type="step_started")

    with pytest.raises(ValueError, match="invalid execution event"):
        log.emit(record)

    validate.assert_called_once_with(record)
    store.insert_execution_log.assert_not_called()
