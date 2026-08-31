"""Local-filesystem adapter for immutable publication manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from metrka_core.catalog.publication_manifest_reader import (
    PublicationManifestFailure,
    PublicationManifestReader,
    PublicationManifestReadError,
)
from metrka_core.storage.portable_paths import validate_portable_relative_path

_SILVER_MANIFESTS_RELATIVE_ROOT = PurePosixPath("files/silver/manifests")


@dataclass(frozen=True, slots=True)
class LocalPublicationManifestReader:
    """Read publication manifests below one resolved workspace data root."""

    data_root: Path
    manifests_root: Path

    def __post_init__(self) -> None:
        for field_name in ("data_root", "manifests_root"):
            value = getattr(self, field_name)

            if not isinstance(value, Path):
                raise TypeError(f"{field_name} must be a pathlib.Path")

            object.__setattr__(self, field_name, value.expanduser().resolve())

    def read_manifest(self, *, path: str) -> dict[str, Any]:
        """Read one manifest without allowing escape from Silver manifest storage."""

        try:
            validate_portable_relative_path(path)
        except ValueError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.UNSAFE_PATH,
                path=path,
                message=f"Publication manifest path is unsafe: {path!r}",
            ) from error

        data_root = self.data_root

        if not data_root.is_dir():
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.NOT_FOUND,
                path=path,
                message=f"Workspace data root does not exist: {data_root}",
            )

        manifests_root = self.manifests_root

        try:
            resolved_manifests_root = manifests_root.resolve(strict=True)
        except FileNotFoundError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.NOT_FOUND,
                path=path,
                message=f"Silver manifest storage does not exist: {manifests_root}",
            ) from error
        except (OSError, RuntimeError) as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.READ_FAILED,
                path=path,
                message=f"Could not resolve Silver manifest storage: {manifests_root}",
            ) from error

        try:
            resolved_manifests_root.relative_to(data_root)
        except ValueError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.OUTSIDE_STORAGE,
                path=path,
                message=f"Silver manifest storage is outside data_root: {manifests_root}",
            ) from error

        relative_path = PurePosixPath(path)
        unresolved_manifest_path = data_root.joinpath(*relative_path.parts)

        try:
            manifest_path = unresolved_manifest_path.resolve(strict=True)
        except FileNotFoundError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.NOT_FOUND,
                path=path,
                message=f"Publication manifest does not exist: {unresolved_manifest_path}",
            ) from error
        except (OSError, RuntimeError) as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.READ_FAILED,
                path=path,
                message=f"Could not resolve publication manifest: {unresolved_manifest_path}",
            ) from error

        try:
            manifest_path.relative_to(resolved_manifests_root)
        except ValueError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.OUTSIDE_STORAGE,
                path=path,
                message=f"Publication manifest is outside Silver manifest storage: {path}",
            ) from error

        if not manifest_path.is_file():
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.NOT_FOUND,
                path=path,
                message=f"Publication manifest is not a file: {manifest_path}",
            )

        try:
            raw_payload = manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.READ_FAILED,
                path=path,
                message=f"Could not read publication manifest: {manifest_path}",
            ) from error

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as error:
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.INVALID_JSON,
                path=path,
                message=f"Publication manifest is not valid JSON: {manifest_path}",
            ) from error

        if not isinstance(payload, dict):
            raise PublicationManifestReadError(
                reason=PublicationManifestFailure.INVALID_OBJECT,
                path=path,
                message=f"Publication manifest must contain a JSON object: {manifest_path}",
            )

        return {str(key): value for key, value in payload.items()}


def create_publication_manifest_reader(*, data_root: Path) -> PublicationManifestReader:
    """Create a reader scoped to one workspace's Silver manifest storage."""

    if not isinstance(data_root, Path):
        raise TypeError("data_root must be a pathlib.Path")

    return LocalPublicationManifestReader(
        data_root=data_root,
        manifests_root=data_root.joinpath(*_SILVER_MANIFESTS_RELATIVE_ROOT.parts),
    )
