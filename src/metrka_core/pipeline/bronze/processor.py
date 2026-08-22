"""Application service for Bronze ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from metrka_core.pipeline.action_runtime import ActionRuntime
from metrka_core.pipeline.bronze.asset_ingestion import BronzeIngestDeps, ingest_landed_assets
from metrka_core.pipeline.bronze.models import BronzeBatchResult
from metrka_core.pipeline.models import LandedAsset


class BronzeProcessor(Protocol):
    """Ingest acquired assets into Bronze."""

    def ingest(self, *, runtime: ActionRuntime, assets: list[LandedAsset]) -> BronzeBatchResult:
        """Process one acquired asset batch."""
        ...


@dataclass(frozen=True)
class ConfiguredBronzeProcessor:
    """Default Bronze processor built by composition."""

    deps: BronzeIngestDeps

    def ingest(self, *, runtime: ActionRuntime, assets: list[LandedAsset]) -> BronzeBatchResult:
        return ingest_landed_assets(runtime=runtime, deps=self.deps, assets=assets)
