"""Compose source acquisition collaborators."""

from __future__ import annotations

from dataclasses import dataclass

from metrka_core.pipeline.acquisition.dependencies import AcquisitionDeps
from metrka_core.pipeline.acquisition.processor import (
    AcquisitionProcessor,
    ConfiguredAcquisitionProcessor,
)
from metrka_core.pipeline.composition.metadata import MetadataComposition
from metrka_core.pipeline.composition.workspace import WorkspaceComposition


@dataclass(frozen=True, slots=True)
class AcquisitionComposition:
    """Dependencies belonging to the acquisition lifecycle phase."""

    processor: AcquisitionProcessor


def build_acquisition_composition(
    *, workspace: WorkspaceComposition, metadata: MetadataComposition
) -> AcquisitionComposition:
    deps = AcquisitionDeps(
        source_config=workspace.source_config,
        landing_store=workspace.landing_store,
        execution_log_store=metadata.execution_logs,
    )

    processor = ConfiguredAcquisitionProcessor(deps=deps, source_captures=metadata.source_captures)

    return AcquisitionComposition(processor=processor)
