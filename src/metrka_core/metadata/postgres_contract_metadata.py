"""PostgreSQL implementation of contract metadata storage."""

from __future__ import annotations

from typing import Any

from metrka_core.metadata.postgres import PostgresSession


class PostgresContractMetadataStore:
    """Persist contract snapshot metadata in PostgreSQL."""

    def __init__(self, session: PostgresSession) -> None:
        self._session = session

    def upsert_contract_snapshot(self, record: dict[str, Any]) -> None:
        """Insert or update one immutable contract snapshot."""

        with self._session.cursor() as cur:
            cur.execute(
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
                ON CONFLICT (contract_hash) DO UPDATE SET
                    dataset = EXCLUDED.dataset,
                    dataset_id = EXCLUDED.dataset_id,
                    contract_name = EXCLUDED.contract_name,
                    contract_stem = EXCLUDED.contract_stem,
                    contract_path = EXCLUDED.contract_path,
                    contract_version = EXCLUDED.contract_version,
                    snapshot_yaml_path = EXCLUDED.snapshot_yaml_path,
                    snapshot_json_path = EXCLUDED.snapshot_json_path
                """,
                (
                    record["contract_hash"],
                    record["dataset"],
                    record.get("dataset_id"),
                    record["contract_name"],
                    record["contract_stem"],
                    record["contract_path"],
                    record.get("contract_version"),
                    record["contract_snapshot_yaml_path"],
                    record.get("contract_snapshot_json_path"),
                ),
            )
