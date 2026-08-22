"""Persistence boundary for source captures."""

from __future__ import annotations

from typing import Protocol

from metrka_core.pipeline.acquisition.models import SourceCapture, SourceCaptureAssetBinding


class SourceCaptureStore(Protocol):
    """Persist source captures and their File Marshal bindings."""

    def register_capture(
        self, *, capture: SourceCapture, pipeline_run_id: str, workspace_name: str
    ) -> None:
        """Register a capture and bind the pipeline run to it."""
        ...

    def bind_assets(
        self, *, source_capture_id: str, assets: tuple[SourceCaptureAssetBinding, ...]
    ) -> None:
        """Bind captured assets to File Marshal identities."""
        ...
