"""Pipeline adapter for Silver processing."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from metrka_core.pipeline.action_models import (
    ActionDefinition,
    ActionDependencyResolver,
    ActionOutcome,
)
from metrka_core.pipeline.action_runtime import ActionRuntime

if TYPE_CHECKING:
    from metrka_core.pipeline.models import PipelineRunState
    from metrka_core.pipeline.registry import PipelineRegistry
    from metrka_core.pipeline.silver.processor import SilverProcessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SilverProcessOptions:
    """Validated options for Silver processing."""

    target_dataset_id: str | None = None
    force_rebuild: bool = False


@dataclass(frozen=True)
class SilverProcessActionDeps:
    """Dependencies required by the Silver action adapter."""

    processor: SilverProcessor


def parse_silver_process_options(raw: Mapping[str, Any]) -> SilverProcessOptions:
    """Validate YAML options for the ``silver.process`` action.

    Supported keys are ``target_dataset_id`` and ``force_rebuild``.
    ``target_dataset_id`` may be a non-empty string or null; null evaluates all
    configured Silver datasets. ``force_rebuild`` must be a boolean and defaults
    to ``False``. Unknown keys or invalid values raise ``ValueError``.
    """

    allowed_options = {"target_dataset_id", "force_rebuild"}

    unexpected_options = set(raw) - allowed_options

    if unexpected_options:
        raise ValueError(
            f"silver.process received unsupported options: {sorted(unexpected_options)}"
        )

    target_dataset_id = raw.get("target_dataset_id")
    force_rebuild = raw.get("force_rebuild", False)

    if not isinstance(force_rebuild, bool):
        raise ValueError("silver.process force_rebuild must be boolean")

    if target_dataset_id is not None and (
        not isinstance(target_dataset_id, str) or not target_dataset_id.strip()
    ):
        raise ValueError("silver.process target_dataset_id must be a non-empty string or null")

    return SilverProcessOptions(
        target_dataset_id=(target_dataset_id.strip() if target_dataset_id is not None else None),
        force_rebuild=force_rebuild,
    )


def process_silver_action(
    *,
    runtime: ActionRuntime,
    deps: SilverProcessActionDeps,
    state: PipelineRunState,
    options: SilverProcessOptions,
) -> ActionOutcome:
    """Process pending Bronze files into Silver."""

    engine_gate = deps.processor.evaluate_engine_gate()

    state.action_results["silver.engine_gate"] = engine_gate

    if not engine_gate.allowed:
        logger.warning(
            "%s Candidate engine=%s; approved engine=%s. Existing publication remains unchanged.",
            engine_gate.message,
            engine_gate.candidate_engine_release_id,
            engine_gate.approved_engine_release_id or "none",
        )

        return ActionOutcome(
            status="skipped",
            message=engine_gate.message,
            metrics={
                "deferred_reason": "silver_engine_approval_required",
                "candidate_engine_release_id": engine_gate.candidate_engine_release_id,
                "approved_engine_release_id": engine_gate.approved_engine_release_id,
            },
        )

    result = deps.processor.process(
        runtime=runtime,
        target_dataset_id=options.target_dataset_id,
        force_rebuild=options.force_rebuild,
    )

    state.action_results["silver.process"] = result

    return ActionOutcome(
        status="completed",
        message="Silver processing completed successfully.",
        metrics={
            "finalized_count": result.finalized_count,
            "skipped_count": result.skipped_count,
            "warning_count": result.warning_count,
            "force_rebuild": options.force_rebuild,
            "target_dataset_id": options.target_dataset_id,
        },
    )


def silver_process_definition(
    *, resolve_dependencies: ActionDependencyResolver[SilverProcessActionDeps]
) -> ActionDefinition[SilverProcessOptions, SilverProcessActionDeps]:
    """Build the registry definition for the ``silver.process`` YAML action."""

    return ActionDefinition(
        key="silver.process",
        parse_options=parse_silver_process_options,
        resolve_dependencies=resolve_dependencies,
        handler=process_silver_action,
    )


def register_silver_actions(
    registry: PipelineRegistry,
    *,
    resolve_dependencies: ActionDependencyResolver[SilverProcessActionDeps],
) -> None:
    """Register the core Silver actions in a pipeline registry."""

    registry.register_action(silver_process_definition(resolve_dependencies=resolve_dependencies))
