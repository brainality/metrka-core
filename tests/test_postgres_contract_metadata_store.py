"""Tests for immutable PostgreSQL contract snapshot registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from metrka_core.metadata.postgres_contract_metadata import PostgresContractMetadataStore

CONTRACT_HASH = "a" * 64


def test_identical_contract_snapshot_registration_is_idempotent() -> None:
    session = MagicMock()
    cursor = session.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = _stored_row()

    PostgresContractMetadataStore(session).register_contract_snapshot(_record())

    assert cursor.execute.call_count == 2
    session.transaction.assert_called_once_with()

    insert_sql, insert_parameters = cursor.execute.call_args_list[0].args
    normalized_insert = " ".join(insert_sql.split())

    assert "ON CONFLICT (contract_hash) DO NOTHING" in normalized_insert
    assert "DO UPDATE" not in normalized_insert
    assert insert_parameters == (
        CONTRACT_HASH,
        "demo",
        "demo.records",
        "records.yaml",
        "records",
        "conf/records.yaml",
        "1.0.0",
        (f"contracts/demo.records/sha256={CONTRACT_HASH}/contract.yaml"),
        (f"contracts/demo.records/sha256={CONTRACT_HASH}/contract.json"),
    )

    select_sql, select_parameters = cursor.execute.call_args_list[1].args

    assert "FROM meta.contract_snapshots" in select_sql
    assert "WHERE contract_hash = %s" in select_sql
    assert select_parameters == (CONTRACT_HASH,)


def test_conflicting_contract_snapshot_registration_is_rejected() -> None:
    session = MagicMock()
    cursor = session.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = _stored_row(dataset_id="another.records")

    with pytest.raises(RuntimeError, match="different immutable metadata"):
        PostgresContractMetadataStore(session).register_contract_snapshot(_record())


def test_missing_persisted_contract_snapshot_is_rejected() -> None:
    session = MagicMock()
    cursor = session.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = None

    with pytest.raises(RuntimeError, match="Contract snapshot was not persisted"):
        PostgresContractMetadataStore(session).register_contract_snapshot(_record())


def _record() -> dict[str, Any]:
    snapshot_root = f"contracts/demo.records/sha256={CONTRACT_HASH}"

    return {
        "contract_hash": CONTRACT_HASH,
        "dataset": "demo",
        "dataset_id": "demo.records",
        "contract_name": "records.yaml",
        "contract_stem": "records",
        "contract_path": "conf/records.yaml",
        "contract_version": "1.0.0",
        "contract_snapshot_yaml_path": f"{snapshot_root}/contract.yaml",
        "contract_snapshot_json_path": f"{snapshot_root}/contract.json",
    }


def _stored_row(*, dataset_id: str = "demo.records") -> dict[str, Any]:
    record = _record()

    return {
        "contract_hash": record["contract_hash"],
        "dataset": record["dataset"],
        "dataset_id": dataset_id,
        "contract_name": record["contract_name"],
        "contract_stem": record["contract_stem"],
        "contract_path": record["contract_path"],
        "contract_version": record["contract_version"],
        "snapshot_yaml_path": record["contract_snapshot_yaml_path"],
        "snapshot_json_path": record["contract_snapshot_json_path"],
    }
