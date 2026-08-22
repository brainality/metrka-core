"""Identifiers for immutable Bronze materializations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class BronzeRunIdGenerator(Protocol):
    """Generate identifiers for Bronze materializations."""

    def new_bronze_run_id(self) -> str:
        """Return one Bronze run identifier."""
        ...


@dataclass(frozen=True)
class UuidBronzeRunIdGenerator:
    """Generate random UUID-based Bronze run identifiers."""

    def new_bronze_run_id(self) -> str:
        return f"bronze_{uuid4().hex[:12]}"
