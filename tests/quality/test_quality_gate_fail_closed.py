from __future__ import annotations

from typing import Any

import pytest

from metrka_core.quality.config import parse_quality_config
from metrka_core.quality.models import (
    QualityCheckInput,
    QualityCheckResult,
    QualityCheckSpec,
    QualityConfig,
    QualityGate,
    QualitySeverity,
)
from metrka_core.quality.registry import QualityRegistry, create_default_quality_registry
from metrka_core.quality.runner import run_quality_gate


class RecordingQualityStore:
    def __init__(self) -> None:
        self.definitions: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []

    def upsert_quality_check_definition(self, record: dict[str, Any]) -> None:
        self.definitions.append(record)

    def insert_quality_check_run(self, record: dict[str, Any]) -> None:
        self.runs.append(record)


def _minimal_check(check_id: str) -> dict[str, object]:
    return {"id": check_id, "type": "sha256_recorded", "severity": "blocking"}


def _complete_config() -> dict[str, object]:
    return {
        "version": 1,
        "gates": {
            "pre_bronze": [_minimal_check("pre-bronze")],
            "post_bronze": [_minimal_check("post-bronze")],
            "pre_silver": [_minimal_check("pre-silver")],
            "post_silver": [_minimal_check("post-silver")],
        },
    }


def test_quality_config_rejects_unknown_applies_to_key() -> None:
    raw = _complete_config()
    gates = raw["gates"]
    assert isinstance(gates, dict)

    pre_bronze = gates["pre_bronze"]
    assert isinstance(pre_bronze, list)
    pre_bronze[0]["applies_to"] = {"is_zipp": True}

    with pytest.raises(ValueError, match="Unsupported applies_to fields.*is_zipp"):
        parse_quality_config(raw)


def test_quality_config_requires_every_non_empty_gate() -> None:
    raw = _complete_config()
    gates = raw["gates"]
    assert isinstance(gates, dict)
    gates.pop("post_silver")

    with pytest.raises(ValueError, match="missing gates.*post_silver"):
        parse_quality_config(raw)


def test_gate_with_no_applicable_checks_is_blocking_error() -> None:
    config = QualityConfig(
        version=1,
        checks=(
            QualityCheckSpec(
                check_id="zip-only",
                check_type="sha256_recorded",
                gate=QualityGate.PRE_BRONZE,
                severity=QualitySeverity.BLOCKING,
                applies_to={"is_zip": True},
            ),
        ),
    )
    store = RecordingQualityStore()

    result = run_quality_gate(
        quality_store=store,
        config=config,
        gate=QualityGate.PRE_BRONZE,
        context={"is_zip": False},
        registry=create_default_quality_registry(),
    )

    assert result.failed is True
    assert result.status == "error"
    assert result.checks_run == 0
    assert result.blocked_count == 1
    assert result.error_count == 1
    assert result.failure_code == "QUALITY_GATE_NO_APPLICABLE_CHECKS"
    assert result.to_meta()["quality_failure_code"] == result.failure_code
    assert store.definitions == []
    assert store.runs == []


def test_gate_with_only_skipped_checks_is_blocking_error() -> None:
    def skipped_runner(check_input: QualityCheckInput) -> QualityCheckResult:
        del check_input
        return QualityCheckResult(
            check_type="always_skipped",
            status="skipped",
            expected={},
            actual={},
            result_summary="No input was available",
            details={},
            params={},
        )

    registry = QualityRegistry()
    registry.register("always_skipped", skipped_runner)
    config = QualityConfig(
        version=1,
        checks=(
            QualityCheckSpec(
                check_id="skipped-check",
                check_type="always_skipped",
                gate=QualityGate.PRE_BRONZE,
                severity=QualitySeverity.BLOCKING,
            ),
        ),
    )

    result = run_quality_gate(
        quality_store=RecordingQualityStore(),
        config=config,
        gate=QualityGate.PRE_BRONZE,
        context={},
        registry=registry,
    )

    assert result.failed is True
    assert result.status == "error"
    assert result.checks_run == 1
    assert result.skipped_count == 1
    assert result.blocked_count == 1
    assert result.failure_code == "QUALITY_GATE_ALL_CHECKS_SKIPPED"
