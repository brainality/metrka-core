"""Assemble the public pipeline context from composed dependencies."""

from __future__ import annotations

from metrka_core.pipeline.composition.acquisition import AcquisitionComposition
from metrka_core.pipeline.composition.bronze import BronzeComposition
from metrka_core.pipeline.composition.metadata import MetadataComposition
from metrka_core.pipeline.composition.runtime import RuntimeComposition
from metrka_core.pipeline.composition.silver import SilverComposition
from metrka_core.pipeline.composition.workspace import WorkspaceComposition
from metrka_core.pipeline.context import PipelineContext


def build_pipeline_context(
    *,
    workspace: WorkspaceComposition,
    runtime: RuntimeComposition,
    metadata: MetadataComposition,
    acquisition: AcquisitionComposition,
    bronze: BronzeComposition,
    silver: SilverComposition,
) -> PipelineContext:
    return PipelineContext(
        runtime=runtime,
        workspace=workspace,
        metadata=metadata,
        acquisition=acquisition,
        bronze=bronze,
        silver=silver,
    )
