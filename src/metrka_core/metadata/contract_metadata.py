"""Persistence contract for contract snapshot metadata."""

from __future__ import annotations

from typing import Any, Protocol


class ContractMetadataStore(Protocol):
    """Persist metadata describing immutable contract snapshots."""

    def register_contract_snapshot(self, record: dict[str, Any]) -> None:
        """Insert one immutable contract snapshot.

        Repeating the same registration is allowed, while conflicting metadata
        for an existing contract hash must be rejected.
        """
        ...
