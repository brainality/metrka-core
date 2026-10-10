"""Application service for configured Silver processing."""

from __future__ import annotations

from dataclasses import dataclass

from metrka_core.pipeline.action_runtime import ActionRuntime
from metrka_core.pipeline.silver.dependencies import SilverProcessDeps
from metrka_core.pipeline.silver.engine_policy import (
    SilverEngineGateDecision,
    evaluate_silver_engine_gate,
)
from metrka_core.pipeline.silver.process_models import SilverProcessResult
from metrka_core.pipeline.silver.task_factory import process_configured_silver


@dataclass(frozen=True)
class ConfiguredSilverProcessor:
    """Default Silver processor assembled at the composition boundary."""

    deps: SilverProcessDeps

    def evaluate_engine_gate(self) -> SilverEngineGateDecision:
        return evaluate_silver_engine_gate(
            runtime=self.deps.engine.runtime, release_store=self.deps.engine.release_store
        )

    def process(
        self,
        *,
        runtime: ActionRuntime,
        target_dataset_id: str | None = None,
        force_rebuild: bool = False,
    ) -> SilverProcessResult:
        return process_configured_silver(
            runtime=runtime,
            deps=self.deps,
            target_dataset_id=target_dataset_id,
            force_rebuild=force_rebuild,
        )
