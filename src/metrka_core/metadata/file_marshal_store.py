"""Persistence contract for source-file lifecycle metadata."""

from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date
from typing import Any, Protocol

from metrka_core.metadata.file_marshal_models import MarshalEntry, MarshalEvent, SilverCandidateFile


class FileMarshalStore(Protocol):
    """Persist and query source-file lifecycle state."""

    def transaction(self) -> AbstractContextManager[Any]: ...

    def upsert_marshaled_file(self, entry: MarshalEntry) -> None: ...

    def insert_marshal_event(self, event: MarshalEvent) -> None: ...

    def get_promoted_fingerprint(self, dataset_id: str) -> dict[str, Any] | None: ...

    def check_hash_exists(self, dataset_id: str, source_hash: str) -> bool: ...

    def get_marshaled_file_by_hash(
        self, dataset_id: str, source_hash: str
    ) -> MarshalEntry | None: ...

    def get_marshaled_file(self, dataset_file_id: str) -> MarshalEntry | None: ...

    def get_promoted_for_version_period(
        self, dataset_id: str, version_period: date
    ) -> MarshalEntry | None: ...

    def get_silver_candidate_files(
        self, *, dataset_id: str | None = None
    ) -> tuple[SilverCandidateFile, ...]: ...
