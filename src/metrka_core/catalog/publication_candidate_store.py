"""Persistence contract for dataset-publication candidates."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from metrka_core.catalog.publication_candidate_models import (
    DatasetPublicationCandidate,
    DatasetPublicationCandidateRequest,
)


class DatasetPublicationCandidateStore(Protocol):
    """Persist proposed public dataset revisions."""

    def register(
        self, request: DatasetPublicationCandidateRequest
    ) -> DatasetPublicationCandidate: ...

    def get_by_id(self, candidate_id: str) -> DatasetPublicationCandidate | None: ...

    def get_by_id_for_update(self, candidate_id: str) -> DatasetPublicationCandidate | None:
        """Lock and return one candidate in an active transaction."""
        ...

    def list_awaiting_approval(
        self, *, dataset_id: str | None = None
    ) -> list[DatasetPublicationCandidate]: ...

    def approve(
        self, *, candidate_id: str, approved_by: str, approved_at: datetime
    ) -> DatasetPublicationCandidate: ...

    def reject(
        self, *, candidate_id: str, rejected_by: str, rejection_reason: str, rejected_at: datetime
    ) -> DatasetPublicationCandidate: ...

    def mark_published(
        self, *, candidate_id: str, publication_id: str
    ) -> DatasetPublicationCandidate: ...
