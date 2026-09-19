"""Grant least-privilege access to the metadata operator role."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_operator_role"
down_revision: str | Sequence[str] | None = "0002_contract_snapshot_immutable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow governance commands without granting schema-owner access."""

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = 'metrka_operator'
            ) THEN
                RAISE EXCEPTION
                    'Required PostgreSQL role metrka_operator is missing. '
                    'Run provision_metadata_roles.sql as a PostgreSQL administrator.';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = 'metrka_operator'
                  AND (
                        NOT rolcanlogin
                        OR rolsuper
                        OR rolcreatedb
                        OR rolcreaterole
                        OR rolinherit
                      )
            ) OR pg_has_role(
                'metrka_operator',
                'metrka_owner',
                'MEMBER'
            ) THEN
                RAISE EXCEPTION
                    'PostgreSQL role metrka_operator is not least-privilege. '
                    'Run provision_metadata_roles.sql as a PostgreSQL administrator.';
            END IF;
        END
        $$
        """
    )

    op.execute(
        """
        GRANT USAGE ON SCHEMA catalog, lineage, logs, meta, quality
        TO metrka_operator
        """
    )
    op.execute(
        """
        GRANT SELECT ON ALL TABLES IN SCHEMA catalog, lineage, logs, meta, quality
        TO metrka_operator
        """
    )
    op.execute(
        """
        GRANT UPDATE ON TABLE
            catalog.dataset_publication_candidates,
            meta.silver_engine_releases
        TO metrka_operator
        """
    )
    op.execute(
        """
        GRANT INSERT, UPDATE ON TABLE
            catalog.dataset_publications,
            catalog.dataset_publication_projection_states
        TO metrka_operator
        """
    )
    op.execute(
        """
        GRANT INSERT ON TABLE
            catalog.dataset_publication_assets,
            quality.asset_integrity_batches,
            quality.asset_integrity_results,
            quality.publication_gate_attempts,
            quality.publication_integrity_checks
        TO metrka_operator
        """
    )
    op.execute(
        """
        GRANT USAGE, SELECT ON SEQUENCE
            quality.asset_integrity_batches_integrity_batch_id_seq,
            quality.publication_gate_attempts_gate_attempt_id_seq
        TO metrka_operator
        """
    )

    for schema_name in ("catalog", "lineage", "logs", "meta", "quality"):
        op.execute(
            f"""
            ALTER DEFAULT PRIVILEGES FOR ROLE metrka_owner
            IN SCHEMA {schema_name}
            GRANT SELECT ON TABLES TO metrka_operator
            """
        )


def downgrade() -> None:
    """Remove application-schema privileges from the operator role."""

    for schema_name in ("catalog", "lineage", "logs", "meta", "quality"):
        op.execute(
            f"""
            ALTER DEFAULT PRIVILEGES FOR ROLE metrka_owner
            IN SCHEMA {schema_name}
            REVOKE SELECT ON TABLES FROM metrka_operator
            """
        )

    op.execute(
        """
        REVOKE USAGE, SELECT ON SEQUENCE
            quality.asset_integrity_batches_integrity_batch_id_seq,
            quality.publication_gate_attempts_gate_attempt_id_seq
        FROM metrka_operator
        """
    )
    op.execute(
        """
        REVOKE INSERT, UPDATE ON TABLE
            catalog.dataset_publications,
            catalog.dataset_publication_projection_states
        FROM metrka_operator
        """
    )
    op.execute(
        """
        REVOKE UPDATE ON TABLE
            catalog.dataset_publication_candidates,
            meta.silver_engine_releases
        FROM metrka_operator
        """
    )
    op.execute(
        """
        REVOKE INSERT ON TABLE
            catalog.dataset_publication_assets,
            quality.asset_integrity_batches,
            quality.asset_integrity_results,
            quality.publication_gate_attempts,
            quality.publication_integrity_checks
        FROM metrka_operator
        """
    )
    op.execute(
        """
        REVOKE SELECT ON ALL TABLES IN SCHEMA catalog, lineage, logs, meta, quality
        FROM metrka_operator
        """
    )
    op.execute(
        """
        REVOKE USAGE ON SCHEMA catalog, lineage, logs, meta, quality
        FROM metrka_operator
        """
    )
