"""Persistence contract for publication reproducibility evidence."""

from __future__ import annotations

from typing import Protocol

from metrka_core.quality.publication_verification_models import (
    SilverPublicationVerification,
    SilverPublicationVerificationRequest,
)


class SilverPublicationVerificationStore(Protocol):
    """Persist aggregated publication reproducibility evidence."""

    def record(
        self, request: SilverPublicationVerificationRequest
    ) -> SilverPublicationVerification: ...
