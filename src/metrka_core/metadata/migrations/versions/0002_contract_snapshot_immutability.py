from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_contract_snapshot_immutable"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Prevent the runtime ETL role from changing registered snapshots."""

    op.execute(
        """
    REVOKE UPDATE, DELETE
    ON TABLE meta.contract_snapshots
    FROM metrka_etl
    """
    )


def downgrade() -> None:
    """Restore the previous ETL permissions."""

    op.execute(
        """
        GRANT UPDATE, DELETE
        ON TABLE meta.contract_snapshots
        TO metrka_etl
        """
    )
