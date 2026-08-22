"""Shared models for data-quality checks and gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class QualityGate(StrEnum):
    """Supported pipeline boundaries for quality checks."""

    PRE_BRONZE = "pre_bronze"
    POST_BRONZE = "post_bronze"
    PRE_SILVER = "pre_silver"
    POST_SILVER = "post_silver"

    @property
    def timing(self) -> str:
        return self.value.split("_", maxsplit=1)[0]

    @property
    def layer(self) -> str:
        return self.value.split("_", maxsplit=1)[1]


class QualitySeverity(StrEnum):
    """Effect of a failed check on pipeline execution."""

    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"

    @property
    def blocks_promotion(self) -> bool:
        return self is QualitySeverity.BLOCKING


class QualityStatus(StrEnum):
    """Possible outcomes of one executed quality check."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class QualityCheckInput:
    """Separated runtime facts and declarative parameters for one check."""

    context: Mapping[str, Any]
    params: Mapping[str, Any]
    check_id: str
    quality_gate: QualityGate
    applies_to: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("Quality check_id must not be empty")

        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
        object.__setattr__(self, "applies_to", MappingProxyType(dict(self.applies_to)))


@dataclass(frozen=True)
class QualityCheckSpec:
    """Declarative specification loaded from quality YAML."""

    check_id: str
    check_type: str
    gate: QualityGate
    severity: QualitySeverity
    name: str | None = None
    description: str | None = None
    applies_to: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.check_id.strip():
            raise ValueError("Quality check_id must not be empty")

        if not self.check_type.strip():
            raise ValueError("Quality check_type must not be empty")


@dataclass(frozen=True)
class QualityConfig:
    """Validated collection of checks loaded from one quality YAML."""

    version: int
    checks: tuple[QualityCheckSpec, ...]

    def checks_for_gate(self, gate: QualityGate) -> tuple[QualityCheckSpec, ...]:
        return tuple(check for check in self.checks if check.gate is gate)


@dataclass(frozen=True)
class QualityCheckResult:
    """Result returned by one quality-check implementation."""

    check_type: str
    status: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    result_summary: str
    details: dict[str, Any]
    params: dict[str, Any]
    duration_ms: int | None = None


@dataclass(frozen=True)
class QualityGateResult:
    """Aggregated result of all checks executed at one gate."""

    status: str
    checks_run: int
    passed_count: int
    failed_count: int
    skipped_count: int
    blocked_count: int
    error_count: int = 0
    failed_check_ids: list[str] = field(default_factory=list)
    error_message: str | None = None
    failure_code: str | None = None

    @property
    def failed(self) -> bool:
        return self.blocked_count > 0

    def to_meta(self) -> dict[str, Any]:
        return {
            "quality_status": self.status,
            "quality_checks_run": self.checks_run,
            "quality_checks_passed": self.passed_count,
            "quality_checks_failed": self.failed_count,
            "quality_checks_skipped": self.skipped_count,
            "blocking_quality_failures": self.blocked_count,
            "quality_checks_errored": self.error_count,
            "failed_check_ids": self.failed_check_ids,
            "quality_failure_code": self.failure_code,
        }
