"""Persistence contract for dataset catalog metadata."""

from __future__ import annotations

from typing import Protocol


class DatasetCatalogStore(Protocol):
    """Persist dataset classification metadata."""

    def register_dataset_catalog_from_contract(
        self, *, dataset_id: str, contract_hash: str, contract: dict[str, object]
    ) -> None:
        """Register category and tags declared by a contract."""
        ...
