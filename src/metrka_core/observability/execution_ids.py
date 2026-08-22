"""Identifiers used by execution-step observability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class ExecutionIdGenerator(Protocol):
    """Generate identifiers for execution runs and steps."""

    def new_run_id(self, prefix: str) -> str:
        """Return an execution run identifier."""
        ...

    def new_step_id(self, prefix: str = "step") -> str:
        """Return an execution step identifier."""
        ...


@dataclass(frozen=True)
class UuidExecutionIdGenerator:
    """Generate random UUID-based execution identifiers."""

    def new_run_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def new_step_id(self, prefix: str = "step") -> str:
        return f"{prefix}_{uuid4().hex[:10]}"
