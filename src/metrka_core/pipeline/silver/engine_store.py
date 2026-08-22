"""Persistence contracts for Silver engine releases."""

from __future__ import annotations

from datetime import datetime
from typing import Final, Protocol

from metrka_core.pipeline.silver.engine_models import SilverEngineIdentity, SilverEngineRelease

DEFAULT_ENGINE_RELEASE_LIST_LIMIT: Final = 50
MAX_ENGINE_RELEASE_LIST_LIMIT: Final = 1000


def require_engine_release_list_limit(limit: int) -> int:
    """Return one valid bounded administrative list size."""

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")

    if not 1 <= limit <= MAX_ENGINE_RELEASE_LIST_LIMIT:
        raise ValueError(
            f"limit must be between 1 and {MAX_ENGINE_RELEASE_LIST_LIMIT}, got {limit}"
        )

    return limit


class SilverEngineReleaseStore(Protocol):
    """Runtime-safe access to Silver engine releases."""

    def register_candidate(
        self, *, identity: SilverEngineIdentity, core_commit_sha: str, detected_at: datetime
    ) -> SilverEngineRelease: ...

    def get_by_id(self, engine_release_id: str) -> SilverEngineRelease | None: ...

    def find_approved(self) -> SilverEngineRelease | None: ...

    def list_releases(
        self, *, limit: int = DEFAULT_ENGINE_RELEASE_LIST_LIMIT
    ) -> list[SilverEngineRelease]: ...


class SilverEngineApprovalStore(Protocol):
    """Administrative mutations for engine approval."""

    def approve(
        self, *, engine_release_id: str, approved_by: str, approved_at: datetime
    ) -> SilverEngineRelease: ...

    def reject(
        self,
        *,
        engine_release_id: str,
        rejected_by: str,
        rejection_reason: str,
        rejected_at: datetime,
    ) -> SilverEngineRelease: ...
