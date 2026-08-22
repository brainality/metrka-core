"""Models describing one immutable capture of source assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from metrka_core.metadata.artifact import ArtifactRole


@dataclass(frozen=True)
class SourceCapture:
    """Identity and directory of one source retrieval event."""

    source_capture_id: str
    captured_at: datetime
    directory: Path
    relative_path: str

    def __post_init__(self) -> None:
        if not self.source_capture_id.strip():
            raise ValueError("SourceCapture.source_capture_id must not be empty")

        if self.captured_at.utcoffset() is None:
            raise ValueError("SourceCapture.captured_at must be timezone-aware")

        if not isinstance(self.directory, Path):
            raise TypeError("SourceCapture.directory must be pathlib.Path")

        if not self.relative_path.strip():
            raise ValueError("SourceCapture.relative_path must not be empty")

        if "\\" in self.relative_path:
            raise ValueError("SourceCapture.relative_path must use '/' separators")

        relative_path = PurePosixPath(self.relative_path)

        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError("SourceCapture.relative_path must be a safe relative path")


@dataclass(frozen=True)
class SourceCaptureAssetReceipt:
    """One asset listed in a source-capture receipt."""

    stream_name: str
    relative_path: str
    source_url: str
    artifact_role: ArtifactRole
    size_bytes: int
    source_last_modified: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stream_name": self.stream_name,
            "relative_path": self.relative_path,
            "source_url": self.source_url,
            "artifact_role": self.artifact_role,
            "size_bytes": self.size_bytes,
            "source_last_modified": (
                self.source_last_modified.isoformat()
                if self.source_last_modified is not None
                else None
            ),
        }


@dataclass(frozen=True)
class SourceCaptureReceipt:
    """Immutable receipt for one completed source capture."""

    source_capture_id: str
    pipeline_run_id: str
    captured_at: datetime
    assets: tuple[SourceCaptureAssetReceipt, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "source_capture_id": self.source_capture_id,
            "pipeline_run_id": self.pipeline_run_id,
            "captured_at": self.captured_at.isoformat(),
            "asset_count": len(self.assets),
            "assets": [asset.to_dict() for asset in self.assets],
        }


@dataclass(frozen=True)
class SourceCaptureAssetBinding:
    """Bind one captured asset to its File Marshal identity."""

    stream_name: str
    dataset_id: str
    dataset_file_id: str
    relative_path: str
    source_url: str
    artifact_role: ArtifactRole
    source_last_modified: datetime | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("stream_name", self.stream_name),
            ("dataset_id", self.dataset_id),
            ("dataset_file_id", self.dataset_file_id),
            ("relative_path", self.relative_path),
            ("source_url", self.source_url),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        relative_path = PurePosixPath(self.relative_path)

        if relative_path.is_absolute() or ".." in relative_path.parts or "\\" in self.relative_path:
            raise ValueError("relative_path must be a safe POSIX path")

        if self.source_last_modified is not None and self.source_last_modified.utcoffset() is None:
            raise ValueError("source_last_modified must be timezone-aware")
