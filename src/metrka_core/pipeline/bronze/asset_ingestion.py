"""Batch ingestion of landed assets into Bronze."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from metrka_core.datasets.source_config import SourceConfig
from metrka_core.metadata.file_ids import DatasetFileIdGenerator
from metrka_core.metadata.file_marshal import FileMarshal
from metrka_core.metadata.file_marshal_store import FileMarshalStore
from metrka_core.observability.stores import ExecutionLogStore
from metrka_core.pipeline.action_runtime import ActionRuntime
from metrka_core.pipeline.bronze.bronze_ingestion import ingest_to_bronze
from metrka_core.pipeline.bronze.models import BronzeBatchResult, BronzeIngestResult
from metrka_core.pipeline.bronze.run_ids import BronzeRunIdGenerator
from metrka_core.pipeline.models import LandedAsset
from metrka_core.pipeline.runtime_services import Clock
from metrka_core.quality.models import QualityConfig
from metrka_core.quality.registry import QualityRegistry
from metrka_core.quality.store import QualityCheckStore
from metrka_core.storage.bronze_store import BronzeArtifactStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BronzeIngestDeps:
    """Dependencies required by Bronze batch ingestion."""

    clock: Clock
    dataset_file_ids: DatasetFileIdGenerator
    bronze_run_ids: BronzeRunIdGenerator
    source_config: SourceConfig
    bronze_store: BronzeArtifactStore
    marshal: FileMarshal
    execution_logs: ExecutionLogStore
    quality_checks: QualityCheckStore
    file_marshal_store: FileMarshalStore
    quality_config: QualityConfig
    quality_registry: QualityRegistry


def ingest_landed_assets(
    *, runtime: ActionRuntime, deps: BronzeIngestDeps, assets: list[LandedAsset]
) -> BronzeBatchResult:
    """
    Register and stage landed assets in Bronze.

    This function provides the generic handoff between acquisition and
    Bronze ingestion. It does not need to know how the assets were acquired.
    """
    source_config = deps.source_config

    ingested_assets: dict[str, BronzeIngestResult] = {}
    new_count = 0
    duplicate_count = 0

    for asset in assets:
        if asset.stream_name not in source_config.streams:
            raise RuntimeError(f"Unknown stream returned by acquisition: {asset.stream_name}")

        stream = source_config.streams[asset.stream_name]
        dataset_id = source_config.dataset_id(asset.stream_name)

        if asset.artifact_role != stream.artifact_role:
            raise RuntimeError(
                f"Artifact role mismatch for stream {asset.stream_name}: "
                f"asset={asset.artifact_role!r}, "
                f"configured={stream.artifact_role!r}"
            )

        if asset.stream_name in ingested_assets:
            raise RuntimeError(
                f"Acquisition returned multiple assets for stream {asset.stream_name}"
            )

        logger.info("Processing landed asset for %s: %s", dataset_id, asset.path.name)

        result = ingest_to_bronze(
            dataset_name=runtime.dataset_name,
            bronze_store=deps.bronze_store,
            marshal=deps.marshal,
            landed_file=asset.path,
            dataset_id=dataset_id,
            source_capture_id=asset.source_capture_id,
            source_url=asset.source_url,
            execution_log_store=deps.execution_logs,
            quality_store=deps.quality_checks,
            file_marshal_store=deps.file_marshal_store,
            clock=deps.clock,
            dataset_file_ids=deps.dataset_file_ids,
            bronze_run_ids=deps.bronze_run_ids,
            artifact_role=asset.artifact_role,
            source_last_modified=asset.source_last_modified,
            quality_config=deps.quality_config,
            quality_registry=deps.quality_registry,
            pipeline_run_id=runtime.pipeline_run_id,
        )

        if result is None:
            raise RuntimeError(f"Bronze ingestion returned no result for {asset.path}")

        ingested_assets[asset.stream_name] = result

        if result.is_new:
            new_count += 1

            logger.info(
                "Registered %s as file %s in Bronze run %s",
                dataset_id,
                result.dataset_file_id,
                result.bronze_run_id,
            )
        else:
            duplicate_count += 1

            logger.info(
                "Skipped duplicate %s; existing file is %s", dataset_id, result.dataset_file_id
            )

    return BronzeBatchResult(
        by_stream=ingested_assets, new_count=new_count, duplicate_count=duplicate_count
    )
