"""
Helpers for writing execution receipts.

Used to log when a step starts, when it finishes,
how long it took and how it ended.
"""

from __future__ import annotations

# ================================================================================
# Imports
# ================================================================================
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any, Literal

from metrka_core.observability.execution_ids import ExecutionIdGenerator, UuidExecutionIdGenerator
from metrka_core.observability.execution_schema import StepStatus, validate_execution_event
from metrka_core.observability.execution_step_meta import ExecutionStepMeta
from metrka_core.observability.stores import ExecutionLogStore
from metrka_core.pipeline.runtime_services import (
    Clock,
    MonotonicClock,
    SystemClock,
    SystemMonotonicClock,
)

# ================================================================================
# Types
# ================================================================================
Layer = Literal["none", "landing", "bronze", "silver"]

VALID_LAYERS = frozenset({"none", "landing", "bronze", "silver"})


# ================================================================================
# Timer
# ===============================================================================
@dataclass
class ExecutionTimer:
    """Measure elapsed execution time."""

    clock: MonotonicClock
    started_at: float = field(init=False)

    def __post_init__(self) -> None:
        self.started_at = self.clock.monotonic()

    def ms(self) -> int:
        """Return non-negative elapsed milliseconds."""

        elapsed_seconds = self.clock.monotonic() - self.started_at

        return int(max(0.0, elapsed_seconds) * 1000)


# ================================================================================
# ExecutionLog
# ===============================================================================
@dataclass(frozen=True)
class ExecutionLog:
    """
    Write execution summary receipts only:

    - step started
    - step finished
    """

    dataset: str
    step: str
    store: ExecutionLogStore = field(compare=False)
    clock: Clock = field(default_factory=SystemClock, compare=False)
    monotonic_clock: MonotonicClock = field(default_factory=SystemMonotonicClock, compare=False)
    ids: ExecutionIdGenerator = field(default_factory=UuidExecutionIdGenerator, compare=False)
    layer: Layer = "none"
    schema_version: int = 1
    run_id: str | None = None
    step_id: str | None = None

    # ---------------------------------------------------------------------------------------------
    # Init / properties
    # ---------------------------------------------------------------------------------------------
    def __post_init__(self) -> None:
        if self.store is None:
            raise ValueError("execution log store is required")

        if self.ids is None:
            raise ValueError("execution ID generator is required")

        if self.clock is None:
            raise ValueError("execution UTC clock is required")

        if self.monotonic_clock is None:
            raise ValueError("execution monotonic clock is required")

        if not isinstance(self.dataset, str) or not self.dataset.strip():
            raise ValueError("dataset must not be blank")

        object.__setattr__(self, "dataset", self.dataset.strip())

        if not isinstance(self.step, str) or not self.step.strip():
            raise ValueError("step must not be blank")

        object.__setattr__(self, "step", self.step.strip())

        if self.layer not in VALID_LAYERS:
            raise ValueError(f"layer must be one of: {sorted(VALID_LAYERS)}")

        if self.run_id is None:
            prefix = self.layer if self.layer != "none" else "run"

            object.__setattr__(self, "run_id", self.ids.new_run_id(prefix))

        if self.step_id is None:
            object.__setattr__(self, "step_id", self.ids.new_step_id())

    def timer(self) -> ExecutionTimer:
        """Return a timer using the injected clock."""

        return ExecutionTimer(clock=self.monotonic_clock)

    # ---------------------------------------------------------------------------------------------
    # Core emitter
    # ---------------------------------------------------------------------------------------------
    def base_record(
        self, *, event_type: str, meta: ExecutionStepMeta | None = None
    ) -> dict[str, Any]:
        """Build the base execution record."""

        occurred_at = self.clock.now_utc()

        if occurred_at.tzinfo is None or occurred_at.utcoffset() != UTC.utcoffset(occurred_at):
            raise ValueError("execution event timestamp must be in UTC")

        rec: dict[str, Any] = {
            "ts": occurred_at.isoformat(timespec="microseconds"),
            "schema_version": self.schema_version,
            "dataset": self.dataset,
            "layer": self.layer,
            "step": self.step,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "event_type": event_type,
        }
        if meta is not None:
            rec["meta"] = meta.to_dict()
        return rec

    def emit(self, record: dict[str, Any]) -> None:
        """Insert into the metadata database."""
        validate_execution_event(record)
        self.store.insert_execution_log(record)

    # ---------------------------------------------------------------------------------------------
    # Step events
    # ---------------------------------------------------------------------------------------------
    def step_started(self, *, meta: ExecutionStepMeta | None = None) -> dict[str, Any]:
        """Write step_started execution receipt."""
        rec = self.base_record(event_type="step_started", meta=meta)
        self.emit(rec)
        return rec

    def step_finished(
        self,
        *,
        status: StepStatus,
        duration_ms: int,
        counts: dict[str, int],
        error: dict[str, Any] | None = None,
        meta: ExecutionStepMeta | None = None,
    ) -> dict[str, Any]:
        """Write step_finished execution receipt."""
        rec = self.base_record(event_type="step_finished", meta=meta)
        rec["status"] = status

        rec["duration_ms"] = duration_ms
        rec["counts"] = counts
        if error is not None:
            rec["error"] = error
        self.emit(rec)
        return rec
