"""Narrow dependency groups used by Silver processing."""

from __future__ import annotations

from dataclasses import dataclass

from metrka_core.catalog.dataset_catalog import DatasetCatalogStore
from metrka_core.datasets.source_config import SourceConfig
from metrka_core.lineage.transformation.ids import TransformationImpactIdGenerator
from metrka_core.lineage.transformation.store import TransformationImpactStore
from metrka_core.metadata.contract_metadata import ContractMetadataStore
from metrka_core.metadata.file_marshal import FileMarshal
from metrka_core.metadata.file_marshal_store import FileMarshalStore
from metrka_core.observability.stores import ExecutionLogStore
from metrka_core.pipeline.runtime_services import Clock
from metrka_core.pipeline.silver.artifact_ports import SilverProcessArtifactStore
from metrka_core.pipeline.silver.build_ids import SilverBuildIdGenerator
from metrka_core.pipeline.silver.build_store import SilverBuildStore
from metrka_core.pipeline.silver.engine_models import SilverEngineRuntime
from metrka_core.pipeline.silver.engine_store import SilverEngineReleaseStore
from metrka_core.pipeline.silver.publication_decision_unit_of_work import (
    SilverPublicationDecisionUnitOfWork,
)
from metrka_core.quality.models import QualityConfig
from metrka_core.quality.registry import QualityRegistry
from metrka_core.quality.store import QualityCheckStore
from metrka_core.storage.bronze_store import BronzeArtifactStore
from metrka_core.storage.config_store import ConfigStore
from metrka_core.storage.contract_store import ContractSnapshotStore


@dataclass(frozen=True)
class SilverInputDeps:
    """Dependencies used to locate and read Bronze inputs."""

    bronze_store: BronzeArtifactStore
    config_store: ConfigStore
    marshal: FileMarshal
    file_marshal_store: FileMarshalStore


@dataclass(frozen=True)
class SilverContractDeps:
    """Dependencies used for contracts and catalog metadata."""

    contract_store: ContractSnapshotStore
    contract_metadata_store: ContractMetadataStore
    dataset_catalog_store: DatasetCatalogStore


@dataclass(frozen=True)
class SilverOutputDeps:
    """Dependencies used to persist Silver materializations."""

    silver_store: SilverProcessArtifactStore
    silver_build_store: SilverBuildStore
    publication_decision_uow: SilverPublicationDecisionUnitOfWork


@dataclass(frozen=True)
class SilverEvidenceDeps:
    """Dependencies used to record execution evidence."""

    execution_log_store: ExecutionLogStore
    quality_store: QualityCheckStore
    transformation_impact_store: TransformationImpactStore
    transformation_impact_ids: TransformationImpactIdGenerator


@dataclass(frozen=True)
class SilverEngineDeps:
    """Dependencies used by the Silver engine gate."""

    runtime: SilverEngineRuntime
    release_store: SilverEngineReleaseStore


@dataclass(frozen=True)
class SilverProcessDeps:
    """Complete dependency projection for the Silver use case."""

    clock: Clock
    build_ids: SilverBuildIdGenerator
    source_config: SourceConfig
    quality_config: QualityConfig
    quality_registry: QualityRegistry
    engine: SilverEngineDeps
    inputs: SilverInputDeps
    contracts: SilverContractDeps
    outputs: SilverOutputDeps
    evidence: SilverEvidenceDeps
