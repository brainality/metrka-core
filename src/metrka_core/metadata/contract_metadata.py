"""Persistence contract for contract snapshot metadata."""

from __future__ import annotations

from typing import Any, Protocol


class ContractMetadataStore(Protocol):
    """Persist metadata describing immutable contract snapshots."""

    def upsert_contract_snapshot(self, record: dict[str, Any]) -> None:
        """Insert or update one contract snapshot metadata row."""
        ...
