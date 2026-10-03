"""Allow one source capture stream to contain multiple physical files."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_source_capture_asset_paths"
down_revision: str | Sequence[str] | None = "0003_operator_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Include relative_path in source-capture asset identity."""

    op.execute(
        """
        ALTER TABLE meta.source_capture_assets
        DROP CONSTRAINT source_capture_assets_pkey
        """
    )

    op.execute(
        """
        ALTER TABLE meta.source_capture_assets
        ADD CONSTRAINT source_capture_assets_pkey
        PRIMARY KEY (
            source_capture_id,
            stream_name,
            relative_path
        )
        """
    )


def downgrade() -> None:
    """Restore the previous one-file-per-stream identity."""

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT
                    source_capture_id,
                    stream_name
                FROM meta.source_capture_assets
                GROUP BY
                    source_capture_id,
                    stream_name
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot restore one source asset per stream: '
                    'meta.source_capture_assets contains multiple paths '
                    'for at least one source capture stream';
            END IF;
        END
        $$
        """
    )

    op.execute(
        """
        ALTER TABLE meta.source_capture_assets
        DROP CONSTRAINT source_capture_assets_pkey
        """
    )

    op.execute(
        """
        ALTER TABLE meta.source_capture_assets
        ADD CONSTRAINT source_capture_assets_pkey
        PRIMARY KEY (
            source_capture_id,
            stream_name
        )
        """
    )
