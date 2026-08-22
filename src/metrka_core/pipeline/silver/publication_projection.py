"""Best-effort refresh of derived Silver projections."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from metrka_core.catalog.publication_models import DatasetPublication
from metrka_core.catalog.publication_projection_models import (
    PublicationProjectionKind,
    PublicationProjectionStatus,
)
from metrka_core.catalog.publication_projection_store import DatasetPublicationProjectionStateStore
from metrka_core.observability.execution_step_meta import ExecutionStepMeta
from metrka_core.observability.execution_step_scope import run_step
from metrka_core.observability.stores import ExecutionLogStore
from metrka_core.pipeline.silver.artifact_ports import WorkspaceRelativePathResolver
from metrka_core.pipeline.silver.publication_indexes import (
    SilverPublicationIndexResult,
    SilverPublicationIndexService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SilverProjectionRefreshResult:
    """Result of refreshing derived publication projections."""

    current_refreshed: bool
    history_refreshed: bool

    @property
    def warning_count(self) -> int:
        """Return the number of failed projection operations."""

        return int(not self.current_refreshed) + int(not self.history_refreshed)


def _projection_error(error: BaseException) -> dict[str, str]:
    return {"type": type(error).__name__, "message": str(error)}


def _record_stale_safely(
    *,
    projection_states: DatasetPublicationProjectionStateStore,
    dataset_id: str,
    projection_kind: PublicationProjectionKind,
    publication_id: str,
    checked_at: datetime,
    error: BaseException,
) -> None:
    """Keep the original projection error authoritative if state persistence also fails."""

    try:
        projection_states.mark_stale(
            dataset_id=dataset_id,
            projection_kind=projection_kind,
            expected_publication_id=publication_id,
            checked_at=checked_at,
            error=_projection_error(error),
        )
    except Exception:
        logger.exception(
            "Could not persist stale %s projection state for dataset_id=%s. "
            "The existing pending state remains the conservative health signal.",
            projection_kind.value,
            dataset_id,
        )


def refresh_current_publication_projection(
    *,
    dataset_id: str,
    publication: DatasetPublication,
    checked_at: datetime,
    publication_indexes: SilverPublicationIndexService,
    projection_states: DatasetPublicationProjectionStateStore,
) -> SilverPublicationIndexResult:
    """Refresh the current projection and persist its resulting health."""

    try:
        result = publication_indexes.refresh_current(dataset_id=dataset_id)

        if result.current_publication.publication_id != publication.publication_id:
            raise RuntimeError(
                "Current projection resolved an unexpected publication: "
                f"expected={publication.publication_id} "
                f"actual={result.current_publication.publication_id}"
            )

        state = projection_states.mark_synchronized(
            dataset_id=dataset_id,
            projection_kind=PublicationProjectionKind.CURRENT,
            publication_id=publication.publication_id,
            checked_at=checked_at,
        )

        if (
            state.status is not PublicationProjectionStatus.SYNCHRONIZED
            or state.expected_publication_id != publication.publication_id
        ):
            raise RuntimeError(
                "Current projection refresh was superseded by publication "
                f"{state.expected_publication_id}"
            )

        return result

    except BaseException as error:
        _record_stale_safely(
            projection_states=projection_states,
            dataset_id=dataset_id,
            projection_kind=PublicationProjectionKind.CURRENT,
            publication_id=publication.publication_id,
            checked_at=checked_at,
            error=error,
        )
        raise


def refresh_history_publication_projection(
    *,
    dataset_id: str,
    expected_publication_id: str,
    checked_at: datetime,
    publication_indexes: SilverPublicationIndexService,
    projection_states: DatasetPublicationProjectionStateStore,
) -> tuple[Path, ...]:
    """Refresh the history projection and persist its resulting health."""

    try:
        paths = publication_indexes.rebuild_history(dataset_id=dataset_id)

        state = projection_states.mark_synchronized(
            dataset_id=dataset_id,
            projection_kind=PublicationProjectionKind.HISTORY,
            publication_id=expected_publication_id,
            checked_at=checked_at,
        )

        if (
            state.status is not PublicationProjectionStatus.SYNCHRONIZED
            or state.expected_publication_id != expected_publication_id
        ):
            raise RuntimeError(
                "History projection refresh was superseded by publication "
                f"{state.expected_publication_id}"
            )

        return paths

    except BaseException as error:
        _record_stale_safely(
            projection_states=projection_states,
            dataset_id=dataset_id,
            projection_kind=PublicationProjectionKind.HISTORY,
            publication_id=expected_publication_id,
            checked_at=checked_at,
            error=error,
        )
        raise


def refresh_silver_publication_projections(
    *,
    dataset_name: str,
    dataset_id: str,
    batch_run_id: str,
    silver_build_id: str,
    current_publication: DatasetPublication,
    history_publication_id: str,
    checked_at: datetime,
    publication_indexes: SilverPublicationIndexService,
    projection_states: DatasetPublicationProjectionStateStore,
    silver_store: WorkspaceRelativePathResolver,
    execution_log_store: ExecutionLogStore,
) -> SilverProjectionRefreshResult:
    """
    Refresh recoverable projections after publication.

    Projection failures never invalidate an already committed
    publication. The reconciler can regenerate both projections.
    """

    reconcile_command = (
        "python -m "
        "metrka_core.pipeline.silver."
        "reconcile_publications "
        f"--workspace {dataset_name} "
        f"--dataset-id {dataset_id}"
    )

    current_refreshed = False
    history_refreshed = False

    try:
        with run_step(
            dataset=dataset_name,
            step="refresh_silver_current_projection",
            layer="silver",
            run_id=batch_run_id,
            start_meta=ExecutionStepMeta(
                dataset_id=dataset_id,
                silver_build_id=silver_build_id,
                extra={
                    "publication_id": current_publication.publication_id,
                    "projection_scope": "current",
                    "recovery_action": "reconcile_publications",
                    "recovery_command": reconcile_command,
                },
            ),
            execution_log_store=execution_log_store,
        ) as index_context:
            index_result = refresh_current_publication_projection(
                dataset_id=dataset_id,
                publication=current_publication,
                checked_at=checked_at,
                publication_indexes=publication_indexes,
                projection_states=projection_states,
            )

            current_refreshed = True

            index_context.count_success(1)

            index_context.set_finish_meta(
                ExecutionStepMeta(
                    extra={
                        "index_refresh_status": "succeeded",
                        "current_publication_id": (index_result.current_publication.publication_id),
                        "latest_pointer_path": silver_store.relative_path(
                            index_result.pointer_path
                        ),
                        "view_paths": [
                            silver_store.relative_path(path) for path in index_result.view_paths
                        ],
                    }
                )
            )

    except Exception:
        if current_refreshed:
            logger.warning(
                "Current projection for publication %s was refreshed, but its "
                "execution-step observability failed.",
                current_publication.publication_id,
                exc_info=True,
            )
        else:
            logger.warning(
                "Silver publication %s for dataset_id=%s "
                "committed successfully, but the current "
                "publication projection could not be refreshed. "
                "Run: %s",
                current_publication.publication_id,
                dataset_id,
                reconcile_command,
                exc_info=True,
            )

    try:
        with run_step(
            dataset=dataset_name,
            step="refresh_silver_history_projection",
            layer="silver",
            run_id=batch_run_id,
            start_meta=ExecutionStepMeta(
                dataset_id=dataset_id,
                silver_build_id=silver_build_id,
                extra={
                    "publication_id": history_publication_id,
                    "projection_scope": "history",
                    "recovery_action": "reconcile_publications",
                    "recovery_command": reconcile_command,
                },
            ),
            execution_log_store=execution_log_store,
        ) as history_context:
            history_paths = refresh_history_publication_projection(
                dataset_id=dataset_id,
                expected_publication_id=history_publication_id,
                checked_at=checked_at,
                publication_indexes=publication_indexes,
                projection_states=projection_states,
            )

            history_refreshed = True

            history_context.count_success(1)

            history_context.set_finish_meta(
                ExecutionStepMeta(
                    extra={
                        "index_refresh_status": "succeeded",
                        "view_paths": [silver_store.relative_path(path) for path in history_paths],
                    }
                )
            )

    except Exception:
        if history_refreshed:
            logger.warning(
                "History projection for publication %s was refreshed, but its "
                "execution-step observability failed.",
                history_publication_id,
                exc_info=True,
            )
        else:
            logger.warning(
                "Silver publication %s for dataset_id=%s "
                "committed successfully, but the history "
                "projection could not be refreshed. Run: %s",
                history_publication_id,
                dataset_id,
                reconcile_command,
                exc_info=True,
            )

    return SilverProjectionRefreshResult(
        current_refreshed=current_refreshed, history_refreshed=history_refreshed
    )
