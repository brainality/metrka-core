"""Compose nondeterministic services for one pipeline run."""

from __future__ import annotations

from dataclasses import dataclass, field

from metrka_core.catalog.publication_ids import (
    PublicationCandidateIdGenerator,
    UuidPublicationCandidateIdGenerator,
)
from metrka_core.lineage.transformation.ids import (
    TransformationImpactIdGenerator,
    UuidTransformationImpactIdGenerator,
)
from metrka_core.metadata.file_ids import DatasetFileIdGenerator, UuidDatasetFileIdGenerator
from metrka_core.metadata.source_schema_ids import (
    SourceSchemaSnapshotIdGenerator,
    UuidSourceSchemaSnapshotIdGenerator,
)
from metrka_core.pipeline.acquisition.source_capture_ids import (
    SourceCaptureIdGenerator,
    UuidSourceCaptureIdGenerator,
)
from metrka_core.pipeline.bronze.run_ids import BronzeRunIdGenerator, UuidBronzeRunIdGenerator
from metrka_core.pipeline.runtime_services import (
    Clock,
    PipelineRunIdGenerator,
    SystemClock,
    UuidPipelineRunIdGenerator,
)
from metrka_core.pipeline.silver.build_ids import SilverBuildIdGenerator, UuidSilverBuildIdGenerator


@dataclass(frozen=True, slots=True)
class RuntimeServices:
    """Nondeterministic services used by one pipeline run."""

    clock: Clock = field(default_factory=SystemClock)
    pipeline_run_ids: PipelineRunIdGenerator = field(default_factory=UuidPipelineRunIdGenerator)
    source_capture_ids: SourceCaptureIdGenerator = field(
        default_factory=UuidSourceCaptureIdGenerator
    )
    dataset_file_ids: DatasetFileIdGenerator = field(default_factory=UuidDatasetFileIdGenerator)
    bronze_run_ids: BronzeRunIdGenerator = field(default_factory=UuidBronzeRunIdGenerator)
    silver_build_ids: SilverBuildIdGenerator = field(default_factory=UuidSilverBuildIdGenerator)
    publication_candidate_ids: PublicationCandidateIdGenerator = field(
        default_factory=UuidPublicationCandidateIdGenerator
    )
    transformation_impact_ids: TransformationImpactIdGenerator = field(
        default_factory=UuidTransformationImpactIdGenerator
    )
    source_schema_snapshot_ids: SourceSchemaSnapshotIdGenerator = field(
        default_factory=UuidSourceSchemaSnapshotIdGenerator
    )
