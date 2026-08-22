"""Architecture guards for consumer-owned Silver artifact ports."""

from __future__ import annotations

import ast
from pathlib import Path


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)


def _direct_methods(node: ast.ClassDef) -> set[str]:
    return {
        child.name
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _protocol_methods(*, node: ast.ClassDef, protocol_classes: dict[str, ast.ClassDef]) -> set[str]:
    methods = _direct_methods(node)

    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in protocol_classes:
            methods.update(
                _protocol_methods(node=protocol_classes[base.id], protocol_classes=protocol_classes)
            )

    return methods


def _is_wide_port_reference(node: ast.AST) -> bool:
    if isinstance(node, ast.ClassDef):
        return node.name == "SilverArtifactStore"

    if isinstance(node, ast.Name):
        return node.id == "SilverArtifactStore"

    return False


def test_local_adapter_satisfies_every_silver_artifact_capability() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    ports_path = (
        repository_root / "src" / "metrka_core" / "pipeline" / "silver" / "artifact_ports.py"
    )
    adapter_path = repository_root / "src" / "metrka_core" / "storage" / "silver_store.py"
    ports_tree = ast.parse(ports_path.read_text(encoding="utf-8"))
    adapter_tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
    protocol_classes = {
        node.name: node for node in ports_tree.body if isinstance(node, ast.ClassDef)
    }
    adapter_methods = _direct_methods(_class(adapter_tree, "LocalSilverArtifactStore"))

    for protocol_name, protocol_class in protocol_classes.items():
        required_methods = _protocol_methods(node=protocol_class, protocol_classes=protocol_classes)
        assert required_methods <= adapter_methods, (
            protocol_name,
            sorted(required_methods - adapter_methods),
        )


def test_obsolete_wide_silver_artifact_store_does_not_return() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "metrka_core"
    references: list[Path] = []

    for source_path in source_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

        if any(_is_wide_port_reference(node) for node in ast.walk(tree)):
            references.append(source_path.relative_to(source_root))

    assert references == []
