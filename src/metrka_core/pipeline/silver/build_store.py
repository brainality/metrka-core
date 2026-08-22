"""Persistence contract for immutable Silver builds."""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime
from typing import Protocol

from metrka_core.pipeline.silver.build_models import SilverBuild


class SilverBuildStore(Protocol):
    """Persist and query immutable Silver build attempts."""

    def insert_started(self, build: SilverBuild) -> str: ...

    def get_by_id(self, silver_build_id: str) -> SilverBuild | None: ...

    def find_by_ids(self, silver_build_ids: Collection[str]) -> dict[str, SilverBuild]: ...

    def list_for_dataset(self, *, dataset_id: str) -> tuple[SilverBuild, ...]: ...

    def find_successful_by_signatures(
        self, build_signatures: Collection[str]
    ) -> dict[str, SilverBuild]: ...

    def find_latest_successful_for_version(
        self, *, dataset_id: str, partition_value: str
    ) -> SilverBuild | None: ...

    def find_latest_attempt_for_version(
        self, *, dataset_id: str, partition_value: str
    ) -> SilverBuild | None: ...

    def mark_succeeded(
        self,
        *,
        silver_build_id: str,
        version_period: date | None,
        partition_key: str | None,
        partition_value: str | None,
        manifest_path: str,
        output_hash: str | None,
        output_file_count: int,
        output_byte_count: int,
        fingerprint_version: int,
        logical_hash_algorithm: str,
        schema_hash_algorithm: str,
        logical_data_hash: str,
        schema_hash: str,
        completed_at: datetime,
    ) -> SilverBuild: ...

    def mark_failed(
        self, *, silver_build_id: str, completed_at: datetime, error_code: str, error_message: str
    ) -> SilverBuild: ...
