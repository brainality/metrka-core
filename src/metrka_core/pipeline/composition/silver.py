"""Compose Silver persistence and publication collaborators."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from metrka_core.catalog.postgres_publication_candidate_store import (
    PostgresDatasetPublicationCandidateStore,
)
from metrka_core.catalog.publication_candidate_store import DatasetPublicationCandidateStore
from metrka_core.catalog.publication_ids import PublicationCandidateIdGenerator
from metrka_core.lineage.transformation.ids import TransformationImpactIdGenerator
from metrka_core.metadata.postgres import PostgresSession
from metrka_core.pipeline.composition.metadata import MetadataComposition
from metrka_core.pipeline.composition.runtime import RuntimeComposition
from metrka_core.pipeline.composition.workspace import WorkspaceComposition
from metrka_core.pipeline.runtime_services import Clock
from metrka_core.pipeline.silver.build_ids import SilverBuildIdGenerator
from metrka_core.pipeline.silver.build_store import SilverBuildStore
from metrka_core.pipeline.silver.dependencies import (
    SilverContractDeps,
    SilverEngineDeps,
    SilverEvidenceDeps,
    SilverInputDeps,
    SilverOutputDeps,
    SilverProcessDeps,
)
from metrka_core.pipeline.silver.engine_models import SilverEngineRuntime
from metrka_core.pipeline.silver.engine_store import SilverEngineReleaseStore
from metrka_core.pipeline.silver.postgres_build_store import PostgresSilverBuildStore
from metrka_core.pipeline.silver.postgres_engine_store import PostgresSilverEngineReleaseStore
from metrka_core.pipeline.silver.postgres_publication_decision_unit_of_work import (
    PostgresSilverPublicationDecisionUnitOfWork,
)
from metrka_core.pipeline.silver.processor import ConfiguredSilverProcessor, SilverProcessor
from metrka_core.pipeline.silver.publication_decision_unit_of_work import (
    SilverPublicationDecisionUnitOfWork,
)
from metrka_core.pipeline.silver.publication_indexes import (
    PublicationBackedSilverIndexService,
    SilverPublicationIndexService,
)
from metrka_core.quality.postgres_publication_verification_store import (
    PostgresSilverPublicationVerificationStore,
)
from metrka_core.quality.publication_verification_store import SilverPublicationVerificationStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SilverComposition:
    """Silver stores and services used by one pipeline execution."""

    processor: SilverProcessor
    silver_builds: SilverBuildStore
    silver_publication_verifications: SilverPublicationVerificationStore
    dataset_publication_candidates: DatasetPublicationCandidateStore
    silver_engine: SilverEngineRuntime
    silver_engine_releases: SilverEngineReleaseStore
    silver_publication_decision_uow: SilverPublicationDecisionUnitOfWork
    silver_publication_indexes: SilverPublicationIndexService


def build_silver_composition(
    *,
    session: PostgresSession,
    workspace: WorkspaceComposition,
    runtime: RuntimeComposition,
    metadata: MetadataComposition,
    clock: Clock,
    build_ids: SilverBuildIdGenerator,
    candidate_ids: PublicationCandidateIdGenerator,
    transformation_impact_ids: TransformationImpactIdGenerator,
) -> SilverComposition:
    """Create governed Silver execution and publication collaborators."""

    silver_engine_releases = PostgresSilverEngineReleaseStore(session)

    silver_engine_release = silver_engine_releases.register_candidate(
        identity=runtime.silver_engine_identity,
        core_commit_sha=runtime.code_provenance.metrka_core.commit_sha,
        detected_at=clock.now_utc(),
    )

    silver_engine = SilverEngineRuntime(
        identity=runtime.silver_engine_identity,
        release=silver_engine_release,
        policy=runtime.silver_engine_policy,
    )

    silver_builds = PostgresSilverBuildStore(session)

    silver_publication_verifications = PostgresSilverPublicationVerificationStore(session)

    dataset_publication_candidates = PostgresDatasetPublicationCandidateStore(session)

    silver_publication_decision_uow = PostgresSilverPublicationDecisionUnitOfWork(
        session=session,
        silver_builds=silver_builds,
        marshal=metadata.marshal,
        publications=metadata.dataset_publications,
        verifications=silver_publication_verifications,
        candidates=dataset_publication_candidates,
        candidate_ids=candidate_ids,
    )

    silver_publication_indexes = PublicationBackedSilverIndexService(
        publications=metadata.dataset_publications,
        publication_assets=metadata.dataset_publication_assets,
        silver_store=workspace.silver_store,
        clock=clock,
    )

    process_deps = SilverProcessDeps(
        clock=clock,
        build_ids=build_ids,
        source_config=workspace.source_config,
        quality_config=workspace.quality_config,
        quality_registry=workspace.quality_registry,
        engine=SilverEngineDeps(runtime=silver_engine, release_store=silver_engine_releases),
        inputs=SilverInputDeps(
            bronze_store=workspace.bronze_store,
            config_store=workspace.config_store,
            marshal=metadata.marshal,
            file_marshal_store=metadata.file_marshal_store,
        ),
        contracts=SilverContractDeps(
            contract_store=workspace.contract_store,
            contract_metadata_store=metadata.contract_metadata,
            dataset_catalog_store=metadata.dataset_catalog,
        ),
        outputs=SilverOutputDeps(
            silver_store=workspace.silver_store,
            silver_build_store=silver_builds,
            publication_decision_uow=silver_publication_decision_uow,
        ),
        evidence=SilverEvidenceDeps(
            execution_log_store=metadata.execution_logs,
            quality_store=metadata.quality_checks,
            transformation_impact_store=metadata.transformation_impacts,
            transformation_impact_ids=transformation_impact_ids,
        ),
    )

    processor = ConfiguredSilverProcessor(deps=process_deps)

    logger.info(
        "Resolved Silver engine %s: status=%s policy=%s engine=%s runtime=%s",
        silver_engine_release.engine_release_id,
        silver_engine_release.status.value,
        runtime.silver_engine_policy.value,
        runtime.silver_engine_identity.engine_hash[:12],
        runtime.silver_engine_identity.runtime_hash[:12],
    )

    return SilverComposition(
        processor=processor,
        silver_builds=silver_builds,
        silver_publication_verifications=silver_publication_verifications,
        dataset_publication_candidates=dataset_publication_candidates,
        silver_engine=silver_engine,
        silver_engine_releases=silver_engine_releases,
        silver_publication_decision_uow=silver_publication_decision_uow,
        silver_publication_indexes=silver_publication_indexes,
    )
