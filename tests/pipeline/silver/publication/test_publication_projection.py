"""Best-effort projection refresh tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from metrka_core.catalog.publication_models import DatasetPublication
from metrka_core.catalog.publication_projection_models import (
    PublicationProjectionKind,
    PublicationProjectionStatus,
)
from metrka_core.pipeline.silver.publication_indexes import SilverPublicationIndexResult
from metrka_core.pipeline.silver.publication_projection import (
    refresh_current_publication_projection,
    refresh_silver_publication_projections,
)

from .fakes import (
    DATASET_ID,
    FIXED_NOW,
    FakePublicationIndexService,
    FakeSilverArtifactStore,
    InMemoryPublicationProjectionStateStore,
    RecordingExecutionLogStore,
    make_publication,
)


def _index_result(publication: DatasetPublication, root: Path) -> SilverPublicationIndexResult:
    return SilverPublicationIndexResult(
        current_publication=publication,
        pointer_path=root / "current.json",
        view_paths=(root / "latest.sql",),
    )


def test_refresh_updates_current_and_history_projections(tmp_path: Path) -> None:
    publication = make_publication()
    indexes = FakePublicationIndexService(
        current_result=_index_result(publication, tmp_path),
        history_paths=(tmp_path / "history.sql",),
    )
    execution_logs = RecordingExecutionLogStore()
    projection_states = InMemoryPublicationProjectionStateStore()
    projection_states.mark_pending(
        dataset_id=DATASET_ID,
        current_publication_id=publication.publication_id,
        history_publication_id=publication.publication_id,
        changed_at=FIXED_NOW,
    )

    result = refresh_silver_publication_projections(
        dataset_name="adult_lead_poisoning",
        dataset_id=DATASET_ID,
        batch_run_id="silver-run-1",
        silver_build_id="build-1",
        current_publication=publication,
        history_publication_id=publication.publication_id,
        checked_at=FIXED_NOW,
        publication_indexes=indexes,
        projection_states=projection_states,
        silver_store=FakeSilverArtifactStore(tmp_path),  # type: ignore[arg-type]
        execution_log_store=execution_logs,
    )

    assert result.current_refreshed
    assert result.history_refreshed
    assert result.warning_count == 0
    assert indexes.current_calls == 1
    assert indexes.history_calls == 1
    for projection_kind in PublicationProjectionKind:
        state = projection_states.get(dataset_id=DATASET_ID, projection_kind=projection_kind)
        assert state is not None
        assert state.status is PublicationProjectionStatus.SYNCHRONIZED
    assert [event.event_type for event in execution_logs.records] == [
        "step_started",
        "step_finished",
        "step_started",
        "step_finished",
    ]


def test_history_refresh_runs_after_current_refresh_failure(tmp_path: Path) -> None:
    publication = make_publication()
    indexes = FakePublicationIndexService(
        current_result=_index_result(publication, tmp_path),
        history_paths=(tmp_path / "history.sql",),
        current_error=RuntimeError("pointer write failed"),
    )
    projection_states = InMemoryPublicationProjectionStateStore()
    projection_states.mark_pending(
        dataset_id=DATASET_ID,
        current_publication_id=publication.publication_id,
        history_publication_id=publication.publication_id,
        changed_at=FIXED_NOW,
    )

    result = refresh_silver_publication_projections(
        dataset_name="adult_lead_poisoning",
        dataset_id=DATASET_ID,
        batch_run_id="silver-run-1",
        silver_build_id="build-1",
        current_publication=publication,
        history_publication_id=publication.publication_id,
        checked_at=FIXED_NOW,
        publication_indexes=indexes,
        projection_states=projection_states,
        silver_store=FakeSilverArtifactStore(tmp_path),  # type: ignore[arg-type]
        execution_log_store=RecordingExecutionLogStore(),
    )

    assert not result.current_refreshed
    assert result.history_refreshed
    assert result.warning_count == 1
    assert indexes.history_calls == 1
    current_state = projection_states.get(
        dataset_id=DATASET_ID, projection_kind=PublicationProjectionKind.CURRENT
    )
    history_state = projection_states.get(
        dataset_id=DATASET_ID, projection_kind=PublicationProjectionKind.HISTORY
    )
    assert current_state is not None
    assert current_state.status is PublicationProjectionStatus.STALE
    assert current_state.error == {"type": "RuntimeError", "message": "pointer write failed"}
    assert history_state is not None
    assert history_state.status is PublicationProjectionStatus.SYNCHRONIZED


def test_both_projection_failures_remain_non_authoritative(tmp_path: Path) -> None:
    publication = make_publication()
    indexes = FakePublicationIndexService(
        current_result=_index_result(publication, tmp_path),
        current_error=RuntimeError("current failed"),
        history_error=RuntimeError("history failed"),
    )
    projection_states = InMemoryPublicationProjectionStateStore()
    projection_states.mark_pending(
        dataset_id=DATASET_ID,
        current_publication_id=publication.publication_id,
        history_publication_id=publication.publication_id,
        changed_at=FIXED_NOW,
    )

    result = refresh_silver_publication_projections(
        dataset_name="adult_lead_poisoning",
        dataset_id=DATASET_ID,
        batch_run_id="silver-run-1",
        silver_build_id="build-1",
        current_publication=publication,
        history_publication_id=publication.publication_id,
        checked_at=FIXED_NOW,
        publication_indexes=indexes,
        projection_states=projection_states,
        silver_store=FakeSilverArtifactStore(tmp_path),  # type: ignore[arg-type]
        execution_log_store=RecordingExecutionLogStore(),
    )

    assert not result.current_refreshed
    assert not result.history_refreshed
    assert result.warning_count == 2
    for projection_kind in PublicationProjectionKind:
        state = projection_states.get(dataset_id=DATASET_ID, projection_kind=projection_kind)
        assert state is not None
        assert state.status is PublicationProjectionStatus.STALE


def test_superseded_refresh_cannot_mark_newer_publication_synchronized(tmp_path: Path) -> None:
    attempted_publication = make_publication(publication_id="publication-1")
    projection_states = InMemoryPublicationProjectionStateStore()
    projection_states.mark_pending(
        dataset_id=DATASET_ID,
        current_publication_id="publication-2",
        history_publication_id="publication-2",
        changed_at=FIXED_NOW,
    )
    indexes = FakePublicationIndexService(
        current_result=_index_result(attempted_publication, tmp_path)
    )

    with pytest.raises(RuntimeError, match="superseded"):
        refresh_current_publication_projection(
            dataset_id=DATASET_ID,
            publication=attempted_publication,
            checked_at=FIXED_NOW,
            publication_indexes=indexes,
            projection_states=projection_states,
        )

    state = projection_states.get(
        dataset_id=DATASET_ID, projection_kind=PublicationProjectionKind.CURRENT
    )
    assert state is not None
    assert state.expected_publication_id == "publication-2"
    assert state.status is PublicationProjectionStatus.PENDING
