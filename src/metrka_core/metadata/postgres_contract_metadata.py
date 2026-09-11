"""PostgreSQL implementation of contract metadata storage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from metrka_core.metadata.postgres import PostgresSession


class PostgresContractMetadataStore:
    """Persist immutable contract snapshot metadata in PostgreSQL."""

    def __init__(self, session: PostgresSession) -> None:
        self._session = session

    def register_contract_snapshot(self, record: dict[str, Any]) -> None:
        """Insert one immutable contract snapshot or verify an identical existing row.

        Repeating the same registration is idempotent. Reusing a contract hash
        with different metadata is rejected.
        """

        expected_identity = _record_identity(record)
        contract_hash = record["contract_hash"]

        with self._session.transaction(), self._session.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO meta.contract_snapshots (
                    contract_hash,
                    dataset,
                    dataset_id,
                    contract_name,
                    contract_stem,
                    contract_path,
                    contract_version,
                    snapshot_yaml_path,
                    snapshot_json_path
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (contract_hash)
                DO NOTHING
                """,
                expected_identity,
            )

            cursor.execute(
                """
            SELECT
                contract_hash,
                dataset,
                dataset_id,
                contract_name,
                contract_stem,
                contract_path,
                contract_version,
                snapshot_yaml_path,
                snapshot_json_path
            FROM meta.contract_snapshots
            WHERE contract_hash = %s

            """,
                (contract_hash,),
            )

            row = cursor.fetchone()

            if row is None:
                raise RuntimeError(f"Contract snapshot was not persisted: {contract_hash}")

            if not isinstance(row, Mapping):
                raise RuntimeError("Contract snapshot lookup returned an invalid database row")

            if _row_identity(row) != expected_identity:
                raise RuntimeError(
                    "Contract hash already exists with different immutable metadata:"
                    f"{contract_hash}"
                )


def _row_identity(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row["contract_hash"],
        row["dataset"],
        row["dataset_id"],
        row["contract_name"],
        row["contract_stem"],
        row["contract_path"],
        row["contract_version"],
        row["snapshot_yaml_path"],
        row["snapshot_json_path"],
    )


def _record_identity(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        record["contract_hash"],
        record["dataset"],
        record.get("dataset_id"),
        record["contract_name"],
        record["contract_stem"],
        record["contract_path"],
        record.get("contract_version"),
        record["contract_snapshot_yaml_path"],
        record.get("contract_snapshot_json_path"),
    )
