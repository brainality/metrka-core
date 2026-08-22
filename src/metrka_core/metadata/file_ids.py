"""Identifiers for immutable source-file identities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class DatasetFileIdGenerator(Protocol):
    """Generate identifiers for File Marshal records."""

    def new_dataset_file_id(self) -> str:
        """Return a PostgreSQL-compatible UUID string."""
        ...


@dataclass(frozen=True)
class UuidDatasetFileIdGenerator:
    """Generate random UUID4 dataset file identifiers."""

    def new_dataset_file_id(self) -> str:
        return str(uuid4())
