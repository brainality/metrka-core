"""Persistence contract for transformation-impact evidence."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from typing import Protocol

from metrka_core.lineage.transformation.models import TransformationImpact


class TransformationImpactStore(Protocol):
    """Persist and query transformation-impact evidence."""

    def insert_many(self, impacts: Iterable[TransformationImpact]) -> list[str]: ...

    def list_for_builds(
        self, *, silver_build_ids: Collection[str]
    ) -> tuple[TransformationImpact, ...]: ...
