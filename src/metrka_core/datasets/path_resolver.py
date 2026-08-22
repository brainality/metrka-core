"""Port for resolving configured workspace locations."""

from __future__ import annotations

from typing import Protocol

from metrka_core.datasets.workspace_location import WorkspaceLocation


class WorkspaceLocationResolver(Protocol):
    """Resolve one configured workspace to its definition and data roots."""

    def resolve(self, workspace_name: str) -> WorkspaceLocation: ...
