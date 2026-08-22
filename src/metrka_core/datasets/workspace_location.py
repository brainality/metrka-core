"""Resolved filesystem locations for one logical Metrka workspace."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class WorkspacePlacement(StrEnum):
    """Supported physical placements for one logical workspace."""

    PORTABLE = "portable"
    MANAGED = "managed"


@dataclass(frozen=True, slots=True)
class WorkspaceLocation:
    """Bind one workspace definition to its persistent data storage."""

    workspace_name: str
    definition_root: Path
    data_root: Path
    workspace_root: Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_name, str) or not self.workspace_name.strip():
            raise ValueError("workspace_name must be a non-empty string")

        object.__setattr__(self, "workspace_name", self.workspace_name.strip())

        for field_name in ("definition_root", "data_root"):
            value = getattr(self, field_name)

            if not isinstance(value, Path):
                raise TypeError(f"{field_name} must be a pathlib.Path")

            object.__setattr__(self, field_name, value.expanduser().resolve())

        if self.definition_root == self.data_root:
            raise ValueError("definition_root and data_root must be different directories")

        if self.workspace_root is None:
            for child, parent in (
                (self.definition_root, self.data_root),
                (self.data_root, self.definition_root),
            ):
                try:
                    child.relative_to(parent)
                except ValueError:
                    continue

                raise ValueError(
                    "Managed definition_root and data_root must not contain one another"
                )

            return

        if not isinstance(self.workspace_root, Path):
            raise TypeError("workspace_root must be a pathlib.Path or None")

        normalized_workspace_root = self.workspace_root.expanduser().resolve()
        object.__setattr__(self, "workspace_root", normalized_workspace_root)

        for field_name in ("definition_root", "data_root"):
            try:
                getattr(self, field_name).relative_to(normalized_workspace_root)
            except ValueError as error:
                raise ValueError(
                    f"{field_name} must be inside workspace_root for a portable workspace"
                ) from error

    @classmethod
    def portable(cls, *, workspace_name: str, workspace_root: Path) -> WorkspaceLocation:
        """Create the conventional all-in-one layout used by existing workspaces."""

        normalized_root = workspace_root.expanduser().resolve()
        return cls(
            workspace_name=workspace_name,
            workspace_root=normalized_root,
            definition_root=normalized_root,
            data_root=normalized_root / "data",
        )

    @classmethod
    def managed(
        cls, *, workspace_name: str, definition_root: Path, data_root: Path
    ) -> WorkspaceLocation:
        """Create a layout whose definitions and data may live in separate stores."""

        return cls(
            workspace_name=workspace_name, definition_root=definition_root, data_root=data_root
        )

    @property
    def is_portable(self) -> bool:
        """Return whether both roots belong to one transferable workspace directory."""

        return self.workspace_root is not None

    @property
    def placement(self) -> WorkspacePlacement:
        """Return the configured physical placement."""

        if self.is_portable:
            return WorkspacePlacement.PORTABLE

        return WorkspacePlacement.MANAGED
