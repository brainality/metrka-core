"""Identifiers for immutable Silver build attempts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class SilverBuildIdGenerator(Protocol):
    """Generate identifiers for Silver build attempts."""

    def new_silver_build_id(self) -> str:
        """Return a PostgreSQL-compatible UUID string."""
        ...


@dataclass(frozen=True)
class UuidSilverBuildIdGenerator:
    """Generate random UUID4 Silver build identifiers."""

    def new_silver_build_id(self) -> str:
        return str(uuid4())
