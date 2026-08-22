"""Protect documentation on registry- and extension-facing contracts."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from metrka_core.metadata import source_schema
from metrka_core.metadata.source_schema import (
    ParsedSourceSchema,
    SourceSchemaChange,
    compare_source_schema_fields,
)
from metrka_core.pipeline.actions import bronze, documentation, silver
from metrka_core.pipeline.silver import (
    manage_engine_releases,
    manage_publication_candidates,
    reconcile_publications,
)
from metrka_core.quality import checks as quality_checks
from metrka_core.quality.checks import basic, fingerprint, table, zip
from metrka_core.quality.checks import bronze as bronze_checks
from metrka_core.quality.checks import files as file_checks
from metrka_core.quality.registry import create_default_quality_registry

CONTRACT_OBJECTS: tuple[tuple[str, Any], ...] = (
    ("parse_bronze_ingest_options", bronze.parse_bronze_ingest_options),
    ("ingest_bronze_action", bronze.ingest_bronze_action),
    ("bronze_ingest_definition", bronze.bronze_ingest_definition),
    ("register_bronze_actions", bronze.register_bronze_actions),
    ("parse_documentation_bind_options", documentation.parse_documentation_bind_options),
    ("bind_documentation_action", documentation.bind_documentation_action),
    ("documentation_bind_definition", documentation.documentation_bind_definition),
    ("register_documentation_actions", documentation.register_documentation_actions),
    ("parse_silver_process_options", silver.parse_silver_process_options),
    ("process_silver_action", silver.process_silver_action),
    ("silver_process_definition", silver.silver_process_definition),
    ("register_silver_actions", silver.register_silver_actions),
    ("source_schema module", source_schema),
    ("ParsedSourceSchema.table_count", ParsedSourceSchema.table_count),
    ("ParsedSourceSchema.field_count", ParsedSourceSchema.field_count),
    ("ParsedSourceSchema.schema_hash_algorithm", ParsedSourceSchema.schema_hash_algorithm),
    ("ParsedSourceSchema.schema_hash", ParsedSourceSchema.schema_hash),
    ("SourceSchemaChange", SourceSchemaChange),
    ("compare_source_schema_fields", compare_source_schema_fields),
    ("manage_engine_releases.main", manage_engine_releases.main),
    ("manage_publication_candidates.main", manage_publication_candidates.main),
    ("reconcile_publications.main", reconcile_publications.main),
)

QUALITY_MODULES: tuple[tuple[str, Any], ...] = (
    ("quality.checks", quality_checks),
    ("quality.checks.basic", basic),
    ("quality.checks.bronze", bronze_checks),
    ("quality.checks.files", file_checks),
    ("quality.checks.fingerprint", fingerprint),
    ("quality.checks.table", table),
    ("quality.checks.zip", zip),
)


@pytest.mark.parametrize(
    ("name", "contract"), CONTRACT_OBJECTS, ids=[x[0] for x in CONTRACT_OBJECTS]
)
def test_registry_and_extension_contracts_have_docstrings(name: str, contract: Any) -> None:
    """Require documentation where callers cannot infer a contract from a call site."""

    assert inspect.getdoc(contract), f"Contract has no docstring: {name}"


@pytest.mark.parametrize(("name", "module"), QUALITY_MODULES, ids=[x[0] for x in QUALITY_MODULES])
def test_builtin_quality_modules_describe_their_contract(name: str, module: Any) -> None:
    """Keep gate-context documentation adjacent to built-in checks."""

    assert inspect.getdoc(module), f"Quality module has no docstring: {name}"


def test_registered_quality_checks_have_docstrings() -> None:
    """Require every built-in registered check to explain inputs and semantics."""

    registry = create_default_quality_registry()

    undocumented = [
        check_type
        for check_type in registry.registered_types
        if not inspect.getdoc(registry.resolve(check_type))
    ]

    assert undocumented == []
