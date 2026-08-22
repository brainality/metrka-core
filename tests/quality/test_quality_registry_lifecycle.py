"""Lifecycle contract for isolated quality-check registries."""

from __future__ import annotations

from inspect import Parameter, signature

import pytest

from metrka_core.quality.models import QualityCheckInput, QualityCheckResult
from metrka_core.quality.registry import create_default_quality_registry
from metrka_core.quality.runner import run_quality_gate


def _custom_check(check_input: QualityCheckInput) -> QualityCheckResult:
    return QualityCheckResult(
        check_type="custom_check",
        status="passed",
        expected={},
        actual={},
        result_summary=f"Executed {check_input.check_id}",
        details={},
        params=dict(check_input.params),
    )


def test_default_quality_registries_have_equal_builtins_but_distinct_identity() -> None:
    first = create_default_quality_registry()
    second = create_default_quality_registry()

    assert first is not second
    assert first.registered_types == second.registered_types


def test_custom_registration_does_not_leak_to_another_registry() -> None:
    first = create_default_quality_registry()
    second = create_default_quality_registry()

    first.register("custom_check", _custom_check)

    assert first.resolve("custom_check") is _custom_check
    with pytest.raises(ValueError, match="No quality-check implementation"):
        second.resolve("custom_check")


def test_quality_gate_requires_an_explicit_registry() -> None:
    registry_parameter = signature(run_quality_gate).parameters["registry"]

    assert registry_parameter.default is Parameter.empty
