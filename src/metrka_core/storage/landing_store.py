"""Storage boundary for landing-zone source captures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from metrka_core.pipeline.acquisition.models import SourceCapture, SourceCaptureReceipt
from metrka_core.pipeline.acquisition.source_capture_ids import SourceCaptureIdGenerator
from metrka_core.pipeline.runtime_services import Clock
from metrka_core.storage.atomic_writes import atomic_write_text
from metrka_core.storage.path_segments import require_path_segment


def _capture_time_from_id(source_capture_id: str) -> datetime:
    parts = source_capture_id.split("_")

    if len(parts) != 3 or parts[0] != "capture":
        raise ValueError("source_capture_id must use capture_YYYYMMDDTHHMMSSZ_<id> format")

    try:
        return datetime.strptime(parts[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"Invalid source_capture_id: {source_capture_id}") from exc


class LandingStore(Protocol):
    """Storage operations required by acquisition actions."""

    def date_dir(self, date_str: str) -> Path:
        """Resolve one landing acquisition date."""
        ...

    def begin_capture(self) -> SourceCapture:
        """Create a new immutable source-capture directory."""
        ...

    def resolve_capture(
        self, *, date_str: str, source_capture_id: str | None = None
    ) -> SourceCapture:
        """Resolve one capture for deterministic backfill."""
        ...

    def allocate_path(self, capture: SourceCapture, original_filename: str) -> Path:
        """Allocate one asset path inside a capture."""
        ...

    def write_receipt(self, capture: SourceCapture, receipt: SourceCaptureReceipt) -> Path:
        """Atomically write the capture receipt."""
        ...


@dataclass(frozen=True)
class LocalLandingStore:
    """Store source captures in a local landing directory."""

    root: Path
    clock: Clock
    source_capture_ids: SourceCaptureIdGenerator

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            raise TypeError("root must be a pathlib.Path")

        object.__setattr__(self, "root", self.root.expanduser().resolve())

    def date_dir(self, date_str: str) -> Path:
        normalized_date = date_str.strip()

        try:
            parsed_date = datetime.strptime(normalized_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date_str must use YYYY-MM-DD format") from exc

        if parsed_date.strftime("%Y-%m-%d") != normalized_date:
            raise ValueError("date_str must use YYYY-MM-DD format")

        return self.root / normalized_date

    def begin_capture(self) -> SourceCapture:
        now = self.clock.now_utc()

        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("Source capture clock must return a timezone-aware UTC datetime")

        now = now.astimezone(UTC)

        source_capture_id = require_path_segment(
            self.source_capture_ids.new_source_capture_id(captured_at=now), "source_capture_id"
        )

        capture_time = _capture_time_from_id(source_capture_id)

        if capture_time != now.replace(microsecond=0):
            raise ValueError("Source capture ID timestamp does not match the capture clock")

        date_folder = now.strftime("%Y-%m-%d")

        capture_dir = self.date_dir(date_folder) / source_capture_id

        capture_dir.mkdir(parents=True, exist_ok=False)

        return SourceCapture(
            source_capture_id=source_capture_id,
            captured_at=now,
            directory=capture_dir.resolve(),
            relative_path=(capture_dir.relative_to(self.root).as_posix()),
        )

    def resolve_capture(
        self, *, date_str: str, source_capture_id: str | None = None
    ) -> SourceCapture:
        target_date_dir = self.date_dir(date_str)

        if not target_date_dir.is_dir():
            raise FileNotFoundError(f"Landing date directory does not exist: {target_date_dir}")

        if source_capture_id is not None:
            normalized_id = require_path_segment(source_capture_id, "source_capture_id")

            capture_dir = target_date_dir / normalized_id

            if not capture_dir.is_dir():
                raise FileNotFoundError(f"Source capture does not exist: {capture_dir}")

            return SourceCapture(
                source_capture_id=normalized_id,
                captured_at=_capture_time_from_id(normalized_id),
                directory=capture_dir.resolve(),
                relative_path=(capture_dir.relative_to(self.root).as_posix()),
            )

        capture_dirs = sorted(
            path
            for path in target_date_dir.iterdir()
            if (path.is_dir() and path.name.startswith("capture_"))
        )

        if len(capture_dirs) == 1:
            capture_dir = capture_dirs[0]

            return SourceCapture(
                source_capture_id=capture_dir.name,
                captured_at=_capture_time_from_id(capture_dir.name),
                directory=capture_dir.resolve(),
                relative_path=(capture_dir.relative_to(self.root).as_posix()),
            )

        if len(capture_dirs) > 1:
            capture_ids = [path.name for path in capture_dirs]

            raise RuntimeError(
                "Multiple source captures found for "
                f"{date_str}: {capture_ids}. "
                "Specify --source-capture-id."
            )

        # Transitional support for existing flat landing folders.
        legacy_files = [path for path in target_date_dir.iterdir() if path.is_file()]

        if legacy_files:
            captured_at = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)

            return SourceCapture(
                source_capture_id=(f"legacy_{date_str}"),
                captured_at=captured_at,
                directory=target_date_dir.resolve(),
                relative_path=(target_date_dir.relative_to(self.root).as_posix()),
            )

        raise FileNotFoundError(f"No source captures found for {date_str}")

    def allocate_path(self, capture: SourceCapture, original_filename: str) -> Path:
        filename = require_path_segment(original_filename.strip(), "original_filename")

        destination = capture.directory / filename

        if destination.exists():
            raise FileExistsError(f"Source-capture asset already exists: {destination}")

        return destination

    def write_receipt(self, capture: SourceCapture, receipt: SourceCaptureReceipt) -> Path:
        if receipt.source_capture_id != capture.source_capture_id:
            raise ValueError("Receipt source_capture_id does not match capture")

        receipt_path = capture.directory / "source_capture.json"
        atomic_write_text(
            receipt_path, json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )

        return receipt_path
