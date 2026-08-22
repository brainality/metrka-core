"""Compose Bronze ingestion collaborators."""

from __future__ import annotations

from dataclasses import dataclass

from metrka_core.metadata.file_ids import DatasetFileIdGenerator
from metrka_core.pipeline.bronze.asset_ingestion import BronzeIngestDeps
from metrka_core.pipeline.bronze.processor import BronzeProcessor, ConfiguredBronzeProcessor
from metrka_core.pipeline.bronze.run_ids import BronzeRunIdGenerator
from metrka_core.pipeline.composition.metadata import MetadataComposition
from metrka_core.pipeline.composition.workspace import WorkspaceComposition
from metrka_core.pipeline.runtime_services import Clock


@dataclass(frozen=True)
class BronzeComposition:
    """Bronze services used by one pipeline execution."""

    processor: BronzeProcessor


def build_bronze_composition(
    *,
    workspace: WorkspaceComposition,
    metadata: MetadataComposition,
    clock: Clock,
    dataset_file_ids: DatasetFileIdGenerator,
    bronze_run_ids: BronzeRunIdGenerator,
) -> BronzeComposition:
    """Build the configured Bronze ingestion service."""

    deps = BronzeIngestDeps(
        clock=clock,
        dataset_file_ids=dataset_file_ids,
        bronze_run_ids=bronze_run_ids,
        source_config=workspace.source_config,
        bronze_store=workspace.bronze_store,
        marshal=metadata.marshal,
        execution_logs=metadata.execution_logs,
        quality_checks=metadata.quality_checks,
        file_marshal_store=metadata.file_marshal_store,
        quality_config=workspace.quality_config,
        quality_registry=workspace.quality_registry,
    )

    return BronzeComposition(processor=ConfiguredBronzeProcessor(deps=deps))
