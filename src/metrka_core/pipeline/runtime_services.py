"""Injectable services for nondeterministic runtime values."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4


class Clock(Protocol):
    """Provide timezone-aware UTC timestamps."""

    def now_utc(self) -> datetime: ...


class MonotonicClock(Protocol):
    """Measure elapsed time independently of UTC."""

    def monotonic(self) -> float:
        """Return monotonically increasing seconds."""
        ...


class PipelineRunIdGenerator(Protocol):
    """Generate identifiers for pipeline executions."""

    def new_pipeline_run_id(self) -> str: ...


@dataclass(frozen=True)
class SystemClock:
    """Read the current time from the operating system."""

    def now_utc(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class SystemMonotonicClock:
    """Read the operating system monotonic clock."""

    def monotonic(self) -> float:
        return time.monotonic()


@dataclass(frozen=True)
class UuidPipelineRunIdGenerator:
    """Generate globally unique pipeline run identifiers."""

    def new_pipeline_run_id(self) -> str:
        return f"pipeline_{uuid4().hex}"
