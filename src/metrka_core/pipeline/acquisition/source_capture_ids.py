"""Identifiers for immutable source captures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4


class SourceCaptureIdGenerator(Protocol):
    """Generate identifiers for immutable source captures."""

    def new_source_capture_id(self, *, captured_at: datetime) -> str:
        """Return one timestamped source-capture identifier."""
        ...


@dataclass(frozen=True)
class UuidSourceCaptureIdGenerator:
    """Generate timestamped source-capture identifiers."""

    def new_source_capture_id(self, *, captured_at: datetime) -> str:
        if captured_at.tzinfo is None or captured_at.utcoffset() != timedelta(0):
            raise ValueError("captured_at must be timezone-aware UTC")

        timestamp = captured_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

        return f"capture_{timestamp}_{uuid4().hex[:8]}"
