from __future__ import annotations

from alembic.script import ScriptDirectory

from metrka_core.metadata.migrations.runner import build_alembic_config


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(build_alembic_config())


def test_metadata_migrations_have_one_current_head() -> None:
    assert _script().get_heads() == ["0003_operator_role"]


def test_metadata_migrations_from_one_linear_history() -> None:
    revisions = list(_script().walk_revisions())

    assert [(revision.revision, revision.down_revision) for revision in revisions] == [
        ("0003_operator_role", "0002_contract_snapshot_immutable"),
        ("0002_contract_snapshot_immutable", "0001_initial"),
        ("0001_initial", None),
    ]


def test_metadata_migration_revision_ids_fit_alembic_ledger() -> None:
    oversized_revisions = {
        revision.revision: len(revision.revision)
        for revision in _script().walk_revisions()
        if len(revision.revision) > 32
    }

    assert oversized_revisions == {}
