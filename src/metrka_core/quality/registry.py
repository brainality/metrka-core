"""Registry of reusable quality-check implementations."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from metrka_core.quality.checks.basic import file_size_min, sha256_recorded
from metrka_core.quality.checks.bronze import bronze_extraction_completed
from metrka_core.quality.checks.files import output_files_created
from metrka_core.quality.checks.fingerprint import payload_fingerprint_recorded
from metrka_core.quality.checks.table import expected_columns_present, has_data_rows
from metrka_core.quality.checks.zip import zip_crc_valid
from metrka_core.quality.models import QualityCheckInput, QualityCheckResult, QualityCheckSpec

QualityCheckRunner = Callable[[QualityCheckInput], QualityCheckResult]


class QualityRegistry:
    """Map stable check types to reusable Python implementations."""

    def __init__(self) -> None:
        self._runners: dict[str, QualityCheckRunner] = {}

    def register(self, check_type: str, runner: QualityCheckRunner) -> None:
        normalized_type = check_type.strip()

        if not normalized_type:
            raise ValueError("Quality check_type must not be empty")

        if normalized_type in self._runners:
            raise ValueError(f"Quality check_type is already registered: {normalized_type}")

        if not callable(runner):
            raise TypeError(f"Quality runner must be callable: {normalized_type}")

        self._runners[normalized_type] = runner

    def resolve(self, check_type: str) -> QualityCheckRunner:
        runner = self._runners.get(check_type)

        if runner is None:
            raise ValueError(
                f"No quality-check implementation registered "
                f"for type {check_type!r}. "
                f"Registered types: "
                f"{list(self.registered_types)}"
            )

        return runner

    def validate_specs(self, specs: Iterable[QualityCheckSpec]) -> None:
        """Ensure every declarative check has an implementation."""

        for spec in specs:
            self.resolve(spec.check_type)

    @property
    def registered_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._runners))


def create_default_quality_registry() -> QualityRegistry:
    """Create the core registry containing built-in checks."""

    registry = QualityRegistry()

    registry.register("file_size_min", file_size_min)
    registry.register("zip_crc_valid", zip_crc_valid)
    registry.register("sha256_recorded", sha256_recorded)
    registry.register("payload_fingerprint_recorded", payload_fingerprint_recorded)

    registry.register("bronze_extraction_completed", bronze_extraction_completed)

    registry.register("output_files_created", output_files_created)

    registry.register("has_data_rows", has_data_rows)
    registry.register("expected_columns_present", expected_columns_present)

    return registry
