"""Identifier ports for source-schema snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class SourceSchemaSnapshotIdGenerator(Protocol):
    """Generate identifiers for source-schema snapshots."""

    def new_source_schema_snapshot_id(self) -> str:
        """Return a PostgreSQL-compatible UUID string."""
        ...


@dataclass(frozen=True)
class UuidSourceSchemaSnapshotIdGenerator:
    """Generate random UUID4 source-schema snapshot IDs."""

    def new_source_schema_snapshot_id(self) -> str:
        return str(uuid4())
