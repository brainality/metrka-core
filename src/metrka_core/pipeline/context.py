"""Shared runtime context for pipeline actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from metrka_core.pipeline.action_runtime import ActionRuntime

if TYPE_CHECKING:
    from metrka_core.pipeline.composition.acquisition import AcquisitionComposition
    from metrka_core.pipeline.composition.bronze import BronzeComposition
    from metrka_core.pipeline.composition.metadata import MetadataComposition
    from metrka_core.pipeline.composition.runtime import RuntimeComposition
    from metrka_core.pipeline.composition.silver import SilverComposition
    from metrka_core.pipeline.composition.workspace import WorkspaceComposition


@dataclass(frozen=True)
class PipelineContext:
    """
    Composed dependencies available at the pipeline boundary.

    Concrete services are grouped by architectural responsibility
    instead of being exposed as one flat collection.
    """

    runtime: RuntimeComposition
    workspace: WorkspaceComposition
    metadata: MetadataComposition
    acquisition: AcquisitionComposition
    bronze: BronzeComposition
    silver: SilverComposition

    def as_action_runtime(self) -> ActionRuntime:
        """Return the infrastructure-free runtime view."""

        return ActionRuntime(
            pipeline_run_id=self.runtime.pipeline_run_id,
            dataset_name=self.workspace.workspace_name,
            code_provenance=self.runtime.code_provenance,
        )
