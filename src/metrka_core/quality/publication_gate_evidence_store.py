"""Port for append-only publication-gate integrity evidence."""

from __future__ import annotations

from typing import Protocol

from metrka_core.quality.publication_gate_evidence_models import PublicationGateAttempt


class PublicationGateEvidenceStore(Protocol):
    """Persist one pre-publication gate attempt and all of its asset results."""

    def insert_attempt(self, attempt: PublicationGateAttempt) -> int:
        """Append the attempt and return its database identity."""

        ...
