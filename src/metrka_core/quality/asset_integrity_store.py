"""Ports for normalized file-integrity evidence persistence."""

from __future__ import annotations

from typing import Protocol

from metrka_core.quality.asset_integrity_models import AssetIntegrityBatch
from metrka_core.quality.publication_integrity_models import (
    PublicationIntegrityBatchLink,
    PublicationIntegrityCheck,
)


class AssetIntegrityBatchStore(Protocol):
    """Persist one generic integrity batch and return its identity."""

    def insert_batch(self, batch: AssetIntegrityBatch) -> int: ...


class PublicationIntegrityBatchLinkStore(Protocol):
    """Attach an existing integrity batch to a publication."""

    def link_batch(self, link: PublicationIntegrityBatchLink) -> None: ...


class PublicationIntegrityCheckStore(Protocol):
    """Atomically persist a new batch and its publication relationship."""

    def insert_check(self, check: PublicationIntegrityCheck) -> int: ...
