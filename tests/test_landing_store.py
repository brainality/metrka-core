"""Tests for immutable local source captures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from metrka_core.storage.landing_store import LocalLandingStore

FIXED_NOW = datetime(2026, 8, 13, 12, 34, 56, tzinfo=UTC)

FIRST_CAPTURE_ID = "capture_20260813T123456Z_11111111"
SECOND_CAPTURE_ID = "capture_20260813T123456Z_22222222"


class FrozenClock:
    """Return one deterministic UTC time."""

    def now_utc(self) -> datetime:
        return FIXED_NOW


class FixedSourceCaptureIds:
    """Return one deterministic capture identifier."""

    def __init__(self, source_capture_id: str) -> None:
        self._source_capture_id = source_capture_id

    def new_source_capture_id(self, *, captured_at: datetime) -> str:
        assert captured_at == FIXED_NOW
        return self._source_capture_id


class SequenceSourceCaptureIds:
    """Return deterministic capture IDs in order."""

    def __init__(self, *source_capture_ids: str) -> None:
        self._source_capture_ids = iter(source_capture_ids)

    def new_source_capture_id(self, *, captured_at: datetime) -> str:
        assert captured_at == FIXED_NOW
        return next(self._source_capture_ids)


def _store(
    tmp_path: Path, *, source_capture_id: str = "capture_20260813T123456Z_a1b2c3d4"
) -> LocalLandingStore:
    return LocalLandingStore(
        root=tmp_path / "landing",
        clock=FrozenClock(),
        source_capture_ids=FixedSourceCaptureIds(source_capture_id),
    )


def test_begin_capture_creates_timestamped_capture_directory(tmp_path: Path) -> None:
    store = _store(tmp_path)

    capture = store.begin_capture()

    assert capture.source_capture_id == "capture_20260813T123456Z_a1b2c3d4"
    assert capture.captured_at == FIXED_NOW
    assert capture.relative_path == "2026-08-13/capture_20260813T123456Z_a1b2c3d4"
    assert capture.directory.is_dir()


def test_separate_capture_ids_do_not_collide(tmp_path: Path) -> None:
    store = LocalLandingStore(
        root=tmp_path / "landing",
        clock=FrozenClock(),
        source_capture_ids=SequenceSourceCaptureIds(FIRST_CAPTURE_ID, SECOND_CAPTURE_ID),
    )

    first = store.begin_capture()
    second = store.begin_capture()

    assert first.directory != second.directory
    assert first.directory.is_dir()
    assert second.directory.is_dir()


def test_allocate_path_preserves_filename_inside_capture(tmp_path: Path) -> None:
    store = _store(tmp_path)
    capture = store.begin_capture()

    path = store.allocate_path(capture, " Inmates final.v2.tar.gz ")

    assert path == capture.directory / "Inmates final.v2.tar.gz"


def test_allocate_path_rejects_existing_asset(tmp_path: Path) -> None:
    store = _store(tmp_path)
    capture = store.begin_capture()

    existing = capture.directory / "source.csv"
    existing.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        store.allocate_path(capture, "source.csv")


@pytest.mark.parametrize("date_str", ["", "2026-8-13", "13-08-2026", "not-a-date"])
def test_date_dir_requires_iso_date(tmp_path: Path, date_str: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _store(tmp_path).date_dir(date_str)


def test_resolve_capture_requires_id_when_date_has_multiple_captures(tmp_path: Path) -> None:
    store = LocalLandingStore(
        root=tmp_path / "landing",
        clock=FrozenClock(),
        source_capture_ids=SequenceSourceCaptureIds(FIRST_CAPTURE_ID, SECOND_CAPTURE_ID),
    )

    first = store.begin_capture()
    store.begin_capture()

    with pytest.raises(RuntimeError, match="Multiple source captures"):
        store.resolve_capture(date_str="2026-08-13")

    resolved = store.resolve_capture(
        date_str="2026-08-13", source_capture_id=first.source_capture_id
    )

    assert resolved.directory == first.directory
