"""Make contract snapshot registrations immutable and dataset-scoped."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_contract_snapshot_immutable"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Scope contract snapshots by dataset and prevent runtime mutation."""

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM meta.contract_snapshots
                WHERE dataset_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot make contract snapshots dataset-scoped: '
                    'meta.contract_snapshots contains NULL dataset_id values';
            END IF;
        END
        $$
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        ALTER COLUMN dataset_id SET NOT NULL
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        DROP CONSTRAINT contract_snapshots_pkey
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        ADD CONSTRAINT contract_snapshots_pkey
        PRIMARY KEY (dataset_id, contract_hash)
        """
    )

    op.execute(
        """
        REVOKE UPDATE, DELETE
        ON TABLE meta.contract_snapshots
        FROM metrka_etl
        """
    )


def downgrade() -> None:
    """Restore global hash identity and the previous ETL permissions."""

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT contract_hash
                FROM meta.contract_snapshots
                GROUP BY contract_hash
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot restore the contract_hash-only primary key: '
                    'one or more hashes are registered for multiple datasets';
            END IF;
        END
        $$
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        DROP CONSTRAINT contract_snapshots_pkey
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        ADD CONSTRAINT contract_snapshots_pkey
        PRIMARY KEY (contract_hash)
        """
    )

    op.execute(
        """
        ALTER TABLE meta.contract_snapshots
        ALTER COLUMN dataset_id DROP NOT NULL
        """
    )

    op.execute(
        """
        GRANT UPDATE, DELETE
        ON TABLE meta.contract_snapshots
        TO metrka_etl
        """
    )
