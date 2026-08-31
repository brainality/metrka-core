"""Consumer-owned ports for focused Silver artifact capabilities."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any, Protocol

from metrka_core.catalog.publication_manifest_reader import PublicationManifestReader
from metrka_core.pipeline.silver.artifact_models import (
    SilverArtifactRef,
    SilverBuildArtifactDeletionResult,
    SilverBuildArtifactQuery,
    SilverBuildRef,
)


class WorkspaceRelativePathResolver(Protocol):
    """Convert managed filesystem paths to workspace-relative paths."""

    def relative_path(self, path: str | Path) -> str: ...


class SilverTableBuildArtifactStore(WorkspaceRelativePathResolver, Protocol):
    """Artifact operations required while building one Silver table."""

    def staging_file_stem(self, *, run_id: str, artifact: SilverArtifactRef) -> Path: ...

    def transformation_details_path(
        self, *, artifact: SilverArtifactRef, transformation_impact_id: str
    ) -> Path: ...


class SilverManifestArtifactWriter(WorkspaceRelativePathResolver, Protocol):
    """Artifact operations required to construct one Silver manifest."""

    @property
    def tables_root(self) -> Path: ...

    def write_manifest(self, *, build: SilverBuildRef, payload: dict[str, Any]) -> Path: ...

    def table_relative_path(self, path: str | Path) -> Path: ...


class SilverBuildFinalizationArtifactStore(SilverManifestArtifactWriter, Protocol):
    """Artifact operations required to make one staged build durable."""

    def commit_staged_files(
        self, *, run_id: str, dataset_id: str, staged_files: list[Path]
    ) -> list[Path]: ...


class SilverStagingCleanupStore(Protocol):
    """Remove finalized staging files."""

    def cleanup_staging(self, *, run_id: str, dataset_id: str) -> None: ...


class SilverLatestViewWriter(Protocol):
    """Write publication-versioned current Silver views."""

    def write_latest_view(self, *, table_key: str, publication_id: str, content: str) -> Path: ...


class SilverHistoryViewWriter(Protocol):
    """Write regenerated Silver history views."""

    def write_history_view(self, *, table_key: str, content: str) -> Path: ...


class SilverPublicationIndexArtifactStore(
    PublicationManifestReader,
    WorkspaceRelativePathResolver,
    SilverLatestViewWriter,
    SilverHistoryViewWriter,
    Protocol,
):
    """Artifact operations required to rebuild publication indexes."""

    def write_latest_pointer(self, *, dataset_id: str, payload: dict[str, Any]) -> Path: ...


class SilverBuildArtifactInventory(Protocol):
    """List local artifact directories belonging to Silver builds."""

    def list_build_artifact_directories(
        self, *, builds: Collection[SilverBuildArtifactQuery] | None = None
    ) -> dict[str, tuple[Path, ...]]: ...


class SilverBuildArtifactStore(SilverBuildArtifactInventory, Protocol):
    """List and remove local Silver build artifact directories."""

    def delete_build_artifact_directories(
        self, *, silver_build_id: str, artifact_directories: Collection[Path] | None = None
    ) -> SilverBuildArtifactDeletionResult: ...


class SilverProcessArtifactStore(
    SilverTableBuildArtifactStore,
    SilverBuildFinalizationArtifactStore,
    SilverStagingCleanupStore,
    Protocol,
):
    """Combined capabilities genuinely required by the complete Silver process."""
