"""Identifier ports for transformation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class TransformationImpactIdGenerator(Protocol):
    """Generate identifiers for transformation-impact records."""

    def new_transformation_impact_id(self) -> str:
        """Return a new transformation-impact identifier."""
        ...


@dataclass(frozen=True)
class UuidTransformationImpactIdGenerator:
    """Generate random UUID4 transformation-impact identifiers."""

    def new_transformation_impact_id(self) -> str:
        return f"impact_{uuid4().hex}"
