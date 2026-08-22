"""
Parses and validates YAML configs for the data ingestion pipeline.

The module reads workspace and stream settings, generates target dataset IDs,
and helps find the correct incoming files in the landing zone.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from metrka_core.metadata.artifact import VALID_ARTIFACT_ROLES, ArtifactRole


@dataclass(frozen=True)
class StreamConfig:
    """Config mapping from source to metrka ingestion."""

    name: str
    official_filename: str
    yaml_contract_name: str | None = None
    artifact_role: ArtifactRole = "data"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceConfig:
    workspace_name: str
    streams: dict[str, StreamConfig]
    pipeline: dict[str, Any] = field(default_factory=dict)

    def dataset_id(self, stream_name: str) -> str:
        """Generate a dataset identifier in 'workspace.stream' format."""
        if stream_name not in self.streams:
            raise KeyError(f"Unknown stream: {stream_name}")
        return f"{self.workspace_name}.{stream_name}"

    def find_landed_file(self, stream_name: str, landing_dir: Path) -> Path | None:
        """Locate a single file in the landing zone matching the stream filename."""
        stream = self.streams[stream_name]
        expected = stream.official_filename.upper()

        matches = [
            path
            for path in landing_dir.iterdir()
            if path.is_file() and path.name.upper().endswith(expected)
        ]

        if len(matches) > 1:
            raise RuntimeError(f"Multiple landed files found for stream {stream_name}: {matches}")

        return matches[0] if matches else None

    def find_landed_file_by_pattern(self, stream_name: str, landing_dir: Path) -> Path | None:
        """Locate multiple files in the landing zone matching the stream filename pattern."""
        stream = self.streams[stream_name]
        pattern = stream.official_filename.casefold()

        matches = sorted(path for path in landing_dir.glob(pattern) if path.is_file())

        if len(matches) > 1:
            raise RuntimeError(f"Multiple landed files found for stream {stream_name}: {matches}")

        return matches[0] if matches else None


def load_source_config(path: str | Path, *, expected_ws_name: str | None = None) -> SourceConfig:
    """Parse and strictly validate a YAML configuration file."""
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    workspace_name = raw.get("workspace_name")
    if not isinstance(workspace_name, str) or not workspace_name.strip():
        raise RuntimeError(f"{path} must define workspace_name")

    if expected_ws_name and workspace_name != expected_ws_name:
        raise RuntimeError(
            f"Unexpected workspace_name in {path}: {workspace_name!r}, "
            f"expected {expected_ws_name!r}"
        )

    raw_streams = raw.get("streams")
    if not isinstance(raw_streams, dict) or not raw_streams:
        raise RuntimeError(f"{path} must define a non-empty streams mapping")

    raw_pipeline = raw.get("pipeline", {})

    if not isinstance(raw_pipeline, dict):
        raise RuntimeError(f"{path}: pipeline must be a mapping")

    streams: dict[str, StreamConfig] = {}

    for stream_name, stream_raw in raw_streams.items():
        if not isinstance(stream_name, str) or not stream_name.strip():
            raise RuntimeError(f"{path}: stream names must be non-empty strings")

        if "." in stream_name:
            raise RuntimeError(f"{path}: stream name must NOT contain '.': {stream_name}")

        if not isinstance(stream_raw, dict):
            raise RuntimeError(f"{path}: stream {stream_name} must be a mapping")

        official_filename = stream_raw.get("official_filename")
        if not isinstance(official_filename, str) or not official_filename.strip():
            raise RuntimeError(f"{path}: stream {stream_name} needs official_filename")

        artifact_role_raw = stream_raw.get("artifact_role", "data")

        if artifact_role_raw not in VALID_ARTIFACT_ROLES:
            raise RuntimeError(
                f"{path}: stream {stream_name} has invalid artifact_role: {artifact_role_raw!r}"
            )

        artifact_role = cast(ArtifactRole, artifact_role_raw)

        known_keys = {"official_filename", "yaml_contract_name", "artifact_role"}
        extra = {key: value for key, value in stream_raw.items() if key not in known_keys}

        streams[stream_name] = StreamConfig(
            name=stream_name,
            official_filename=official_filename,
            yaml_contract_name=stream_raw.get("yaml_contract_name"),
            artifact_role=artifact_role,
            extra=extra,
        )

    return SourceConfig(workspace_name=workspace_name, streams=streams, pipeline=dict(raw_pipeline))
