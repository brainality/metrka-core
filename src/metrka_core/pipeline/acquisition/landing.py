"""Acquisition of files already present in the landing zone."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from metrka_core.datasets.source_config import SourceConfig
from metrka_core.pipeline.acquisition.contracts import AssetExtractor
from metrka_core.pipeline.acquisition.dependencies import AcquisitionDeps
from metrka_core.pipeline.acquisition.models import SourceCaptureAssetReceipt, SourceCaptureReceipt
from metrka_core.pipeline.action_runtime import ActionRuntime
from metrka_core.pipeline.models import (
    AcquisitionResult,
    BackfillSourceLastModifiedMode,
    LandedAsset,
)

logger = logging.getLogger(__name__)


LandingMatchMode = Literal["exact", "pattern"]


def collect_landed_assets(
    *,
    source_config: SourceConfig,
    target_dir: Path,
    source_capture_id: str,
    source_url: str = "manual_upload",
    match_mode: LandingMatchMode = "exact",
    source_last_modified_from: BackfillSourceLastModifiedMode = "none",
    target_date: str | None = None,
) -> list[LandedAsset]:
    """
    Find files in a landing directory using configured stream filenames.

    Exact mode matches a configured official filename.
    Pattern mode treats the configured filename as a glob pattern.
    """

    if not target_dir.exists():
        raise FileNotFoundError(f"Landing directory does not exist: {target_dir}")

    if not target_dir.is_dir():
        raise NotADirectoryError(f"Landing path is not a directory: {target_dir}")

    target_date_modified: datetime | None = None

    if source_last_modified_from == "target_date":
        if target_date is None:
            raise ValueError("target_date is required when source_last_modified_from='target_date'")

        try:
            target_date_modified = datetime.strptime(target_date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError as exc:
            raise ValueError("target_date must use YYYY-MM-DD format") from exc

    landed_assets: list[LandedAsset] = []

    for stream_name, stream in source_config.streams.items():
        if match_mode == "exact":
            landed_file = source_config.find_landed_file(stream_name, target_dir)
        elif match_mode == "pattern":
            landed_file = source_config.find_landed_file_by_pattern(stream_name, target_dir)
        else:
            raise ValueError(f"Unsupported landing match mode: {match_mode}")

        if landed_file is None:
            logger.warning("No landed file found for stream %s in %s", stream_name, target_dir)
            continue

        source_last_modified = None

        if source_last_modified_from == "file_mtime":
            source_last_modified = datetime.fromtimestamp(landed_file.stat().st_mtime, tz=UTC)

        elif source_last_modified_from == "target_date":
            if stream.artifact_role == "data":
                source_last_modified = target_date_modified
            else:
                source_last_modified = datetime.fromtimestamp(landed_file.stat().st_mtime, tz=UTC)

        landed_assets.append(
            LandedAsset(
                stream_name=stream_name,
                path=landed_file,
                source_capture_id=source_capture_id,
                source_url=source_url,
                artifact_role=stream.artifact_role,
                source_last_modified=source_last_modified,
            )
        )

    logger.info("Collected %d landed assets from %s", len(landed_assets), target_dir)

    return landed_assets


def acquire_assets(
    *,
    runtime: ActionRuntime,
    deps: AcquisitionDeps,
    target_date: str | None,
    target_source_capture_id: str | None,
    scheduled_extractor: AssetExtractor,
    extractor_options: dict[str, Any],
    backfill_source_url: str = "manual_upload",
    backfill_match_mode: LandingMatchMode = "exact",
    backfill_source_last_modified_from: BackfillSourceLastModifiedMode = "none",
) -> AcquisitionResult:
    """
    Acquire assets for either a backfill or a scheduled pipeline run.

    Backfill runs collect files already present in landing.
    Scheduled runs invoke the supplied source-specific extractor.
    """

    if target_date is not None:
        logger.info("BACKFILL MODE: Collecting landed assets for date %s", target_date)

        capture = deps.landing_store.resolve_capture(
            date_str=target_date, source_capture_id=target_source_capture_id
        )

        logger.info("Using source capture %s from %s", capture.source_capture_id, capture.directory)

        landed_assets = collect_landed_assets(
            source_config=deps.source_config,
            target_dir=capture.directory,
            source_capture_id=capture.source_capture_id,
            source_url=backfill_source_url,
            match_mode=backfill_match_mode,
            source_last_modified_from=backfill_source_last_modified_from,
            target_date=target_date,
        )

        return AcquisitionResult(source_capture=capture, landed_assets=tuple(landed_assets))

    logger.info("SCHEDULED MODE: Running configured source extractor.")

    capture = deps.landing_store.begin_capture()

    logger.info("Created source capture %s at %s", capture.source_capture_id, capture.directory)

    landed_assets = scheduled_extractor(runtime, deps, capture, dict(extractor_options))

    receipt = SourceCaptureReceipt(
        source_capture_id=capture.source_capture_id,
        pipeline_run_id=runtime.pipeline_run_id,
        captured_at=capture.captured_at,
        assets=tuple(
            SourceCaptureAssetReceipt(
                stream_name=asset.stream_name,
                relative_path=asset.path.relative_to(capture.directory).as_posix(),
                source_url=asset.source_url,
                artifact_role=asset.artifact_role,
                size_bytes=asset.path.stat().st_size,
                source_last_modified=asset.source_last_modified,
            )
            for asset in landed_assets
        ),
    )

    receipt_path = deps.landing_store.write_receipt(capture, receipt)

    logger.info("Wrote source-capture receipt: %s", receipt_path)

    return AcquisitionResult(source_capture=capture, landed_assets=tuple(landed_assets))
