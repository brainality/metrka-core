"""Build the local workspace used by one pipeline execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from metrka_core.datasets.path_resolver import WorkspaceLocationResolver
from metrka_core.datasets.source_config import SourceConfig, load_source_config
from metrka_core.pipeline.acquisition.source_capture_ids import SourceCaptureIdGenerator
from metrka_core.pipeline.config import parse_quality_settings
from metrka_core.pipeline.runtime_services import Clock
from metrka_core.quality.config import load_quality_config
from metrka_core.quality.models import QualityConfig
from metrka_core.quality.registry import QualityRegistry, create_default_quality_registry
from metrka_core.storage.bronze_store import BronzeArtifactStore, LocalBronzeArtifactStore
from metrka_core.storage.config_store import ConfigStore, LocalConfigStore
from metrka_core.storage.contract_store import ContractSnapshotStore, LocalContractSnapshotStore
from metrka_core.storage.landing_store import LandingStore, LocalLandingStore
from metrka_core.storage.silver_store import LocalSilverArtifactStore
from metrka_core.storage.workspace_initializer import LocalWorkspaceInitializer
from metrka_core.storage.workspace_layout import WorkspaceLayout

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkspaceComposition:
    """Resolved local storage and configuration for one workspace."""

    workspace_name: str
    layout: WorkspaceLayout
    landing_store: LandingStore
    bronze_store: BronzeArtifactStore
    silver_store: LocalSilverArtifactStore
    config_store: ConfigStore
    contract_store: ContractSnapshotStore
    source_config: SourceConfig
    quality_config: QualityConfig
    quality_registry: QualityRegistry


def build_workspace_composition(
    *,
    workspace_name: str,
    config_name: str,
    workspace_locations: WorkspaceLocationResolver,
    clock: Clock,
    source_capture_ids: SourceCaptureIdGenerator,
) -> WorkspaceComposition:
    """Resolve and validate the local pipeline workspace."""

    if not workspace_name.strip():
        raise ValueError("workspace_name must not be empty")

    location = workspace_locations.resolve(workspace_name)

    if location.workspace_name != workspace_name:
        raise ValueError(
            "WorkspaceLocationResolver returned a location for a different workspace: "
            f"{location.workspace_name!r}"
        )

    layout = WorkspaceLayout(location=location)

    LocalWorkspaceInitializer(layout=layout).ensure_structure()

    landing_store = LocalLandingStore(
        root=layout.bronze_landing_dir, clock=clock, source_capture_ids=source_capture_ids
    )

    bronze_store = LocalBronzeArtifactStore(
        workspace_root=layout.data_root,
        bronze_root=layout.bronze_dir,
        current_root=layout.current_dir,
    )

    silver_store = LocalSilverArtifactStore(
        workspace_root=layout.data_root,
        silver_root=layout.silver_dir,
        current_root=layout.current_dir,
    )

    config_store = LocalConfigStore(
        workspace_root=layout.definition_root, config_root=layout.conf_dir
    )

    contract_store = LocalContractSnapshotStore(
        definition_root=layout.definition_root,
        data_root=layout.data_root,
        snapshots_root=layout.contract_snapshots_dir,
    )

    source_config = load_source_config(
        config_store.path(name=config_name), expected_ws_name=workspace_name
    )

    quality_settings = parse_quality_settings(source_config.pipeline.get("quality"))

    quality_config = load_quality_config(config_store.path(name=quality_settings.config))

    quality_registry = create_default_quality_registry()
    quality_registry.validate_specs(quality_config.checks)

    logger.info(
        "Loaded quality config %s with %d checks",
        quality_settings.config,
        len(quality_config.checks),
    )

    return WorkspaceComposition(
        workspace_name=workspace_name,
        layout=layout,
        landing_store=landing_store,
        bronze_store=bronze_store,
        silver_store=silver_store,
        config_store=config_store,
        contract_store=contract_store,
        source_config=source_config,
        quality_config=quality_config,
        quality_registry=quality_registry,
    )
