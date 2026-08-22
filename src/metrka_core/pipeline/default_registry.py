"""Default composition of reusable Metrka pipeline components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from metrka_core.pipeline.acquisition.http_files import extract_http_files
from metrka_core.pipeline.actions.bronze import BronzeIngestActionDeps, register_bronze_actions
from metrka_core.pipeline.actions.documentation import (
    DocumentationBindDeps,
    register_documentation_actions,
)
from metrka_core.pipeline.actions.silver import SilverProcessActionDeps, register_silver_actions
from metrka_core.pipeline.registry import PipelineRegistry

if TYPE_CHECKING:
    from metrka_core.pipeline.context import PipelineContext


def _resolve_bronze_dependencies(context: PipelineContext) -> BronzeIngestActionDeps:
    return BronzeIngestActionDeps(
        processor=context.bronze.processor, source_captures=context.metadata.source_captures
    )


def _resolve_documentation_dependencies(context: PipelineContext) -> DocumentationBindDeps:
    return DocumentationBindDeps(
        source_config=context.workspace.source_config,
        execution_logs=context.metadata.execution_logs,
    )


def _resolve_silver_dependencies(context: PipelineContext) -> SilverProcessActionDeps:
    return SilverProcessActionDeps(processor=context.silver.processor)


def create_core_registry() -> PipelineRegistry:
    """Create the standard registry used by Metrka pipelines."""

    registry = PipelineRegistry()

    registry.register_extractor("http.files", extract_http_files)

    register_bronze_actions(registry, resolve_dependencies=_resolve_bronze_dependencies)
    register_documentation_actions(
        registry, resolve_dependencies=_resolve_documentation_dependencies
    )
    register_silver_actions(registry, resolve_dependencies=_resolve_silver_dependencies)

    return registry
