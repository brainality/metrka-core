"""Application service for source acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from metrka_core.pipeline.acquisition.contracts import AssetExtractor
from metrka_core.pipeline.acquisition.dependencies import AcquisitionDeps
from metrka_core.pipeline.acquisition.landing import LandingMatchMode, acquire_assets
from metrka_core.pipeline.acquisition.source_capture_store import SourceCaptureStore
from metrka_core.pipeline.action_runtime import ActionRuntime
from metrka_core.pipeline.models import AcquisitionResult, BackfillSourceLastModifiedMode


class AcquisitionProcessor(Protocol):
    """Execute the mandatory acquisition lifecycle phase."""

    def acquire(
        self,
        *,
        runtime: ActionRuntime,
        target_date: str | None,
        target_source_capture_id: str | None,
        scheduled_extractor: AssetExtractor,
        extractor_options: dict[str, Any],
        backfill_source_url: str,
        backfill_match_mode: LandingMatchMode,
        backfill_source_last_modified_from: BackfillSourceLastModifiedMode,
    ) -> AcquisitionResult:
        """Acquire assets and register their source capture."""
        ...


@dataclass(frozen=True, slots=True)
class ConfiguredAcquisitionProcessor:
    """Default acquisition processor composed by metrka-core."""

    deps: AcquisitionDeps
    source_captures: SourceCaptureStore

    def acquire(
        self,
        *,
        runtime: ActionRuntime,
        target_date: str | None,
        target_source_capture_id: str | None,
        scheduled_extractor: AssetExtractor,
        extractor_options: dict[str, Any],
        backfill_source_url: str,
        backfill_match_mode: LandingMatchMode,
        backfill_source_last_modified_from: BackfillSourceLastModifiedMode,
    ) -> AcquisitionResult:
        result = acquire_assets(
            runtime=runtime,
            deps=self.deps,
            target_date=target_date,
            target_source_capture_id=target_source_capture_id,
            scheduled_extractor=scheduled_extractor,
            extractor_options=extractor_options,
            backfill_source_url=backfill_source_url,
            backfill_match_mode=backfill_match_mode,
            backfill_source_last_modified_from=backfill_source_last_modified_from,
        )

        self.source_captures.register_capture(
            capture=result.source_capture,
            pipeline_run_id=runtime.pipeline_run_id,
            workspace_name=runtime.dataset_name,
        )

        return result
