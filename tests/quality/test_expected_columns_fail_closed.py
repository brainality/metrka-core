from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from metrka_core.quality.checks.table import expected_columns_present
from metrka_core.quality.models import (
    QualityCheckInput,
    QualityCheckSpec,
    QualityConfig,
    QualityGate,
    QualitySeverity,
)
from metrka_core.quality.registry import create_default_quality_registry
from metrka_core.quality.runner import run_quality_gate


@dataclass(frozen=True)
class TableStub:
    columns: tuple[str, ...]


class RecordingQualityStore:
    def __init__(self) -> None:
        self.definitions: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []

    def upsert_quality_check_definition(self, record: dict[str, Any]) -> None:
        self.definitions.append(record)

    def insert_quality_check_run(self, record: dict[str, Any]) -> None:
        self.runs.append(record)


def _context(**overrides: Any) -> dict[str, Any]:
    context: dict[str, Any] = {
        "table": TableStub(columns=("id", "name")),
        "allow_extra_columns": True,
    }
    context.update(overrides)
    return context


def _input(context: dict[str, Any], *, params: dict[str, Any] | None = None) -> QualityCheckInput:
    return QualityCheckInput(
        context=context,
        params=params or {},
        check_id="expected-columns",
        quality_gate=QualityGate.PRE_SILVER,
        applies_to={},
    )


def test_check_requires_expected_columns_key() -> None:
    with pytest.raises(KeyError, match="requires 'expected_columns'"):
        expected_columns_present(_input(_context()))


def test_check_rejects_empty_expected_columns() -> None:
    with pytest.raises(ValueError, match="non-empty expected column list"):
        expected_columns_present(_input(_context(expected_columns=[])))


def test_check_rejects_non_list_expected_columns() -> None:
    with pytest.raises(TypeError, match="'expected_columns' to be a list"):
        expected_columns_present(_input(_context(expected_columns=("id", "name"))))


def test_check_requires_explicit_extra_column_policy() -> None:
    context = _context(expected_columns=["id", "name"])
    del context["allow_extra_columns"]

    with pytest.raises(KeyError, match="requires 'allow_extra_columns'"):
        expected_columns_present(_input(context))


def test_check_rejects_non_boolean_extra_column_policy() -> None:
    with pytest.raises(TypeError, match="'allow_extra_columns' to be a boolean"):
        expected_columns_present(
            _input(_context(expected_columns=["id", "name"], allow_extra_columns="false"))
        )


def test_check_compares_a_real_expected_column_list() -> None:
    result = expected_columns_present(_input(_context(expected_columns=["id", "name"])))

    assert result.status == "passed"
    assert result.expected == {"columns": ["id", "name"], "allow_extra_columns": True}
    assert result.actual["missing_columns"] == []


def test_check_rejects_extra_columns_when_policy_is_false() -> None:
    result = expected_columns_present(
        _input(_context(expected_columns=["id"], allow_extra_columns=False))
    )

    assert result.status == "failed"
    assert result.actual["unexpected_columns"] == ["name"]


@pytest.mark.parametrize(
    ("context", "missing_key"),
    [
        (_context(), "expected_columns"),
        (
            {"table": TableStub(columns=("id", "name")), "expected_columns": ["id", "name"]},
            "allow_extra_columns",
        ),
    ],
)
def test_runner_records_missing_input_as_blocking_error(
    context: dict[str, Any], missing_key: str
) -> None:
    store = RecordingQualityStore()
    config = QualityConfig(
        version=1,
        checks=(
            QualityCheckSpec(
                check_id="expected-columns",
                check_type="expected_columns_present",
                gate=QualityGate.PRE_SILVER,
                severity=QualitySeverity.BLOCKING,
            ),
        ),
    )

    result = run_quality_gate(
        quality_store=store,
        config=config,
        gate=QualityGate.PRE_SILVER,
        context=context,
        registry=create_default_quality_registry(),
    )

    assert result.failed is True
    assert result.status == "failed"
    assert result.checks_run == 1
    assert result.error_count == 1
    assert result.blocked_count == 1
    assert result.failed_check_ids == ["expected-columns"]

    assert len(store.runs) == 1
    assert store.runs[0]["status"] == "error"
    assert store.runs[0]["details"]["error_type"] == "KeyError"
    assert f"requires '{missing_key}'" in store.runs[0]["result_summary"]


def test_params_cannot_shadow_runtime_context() -> None:
    store = RecordingQualityStore()
    config = QualityConfig(
        version=1,
        checks=(
            QualityCheckSpec(
                check_id="expected-columns",
                check_type="expected_columns_present",
                gate=QualityGate.PRE_SILVER,
                severity=QualitySeverity.BLOCKING,
                params={"allow_extra_columns": True},
            ),
        ),
    )

    result = run_quality_gate(
        quality_store=store,
        config=config,
        gate=QualityGate.PRE_SILVER,
        context=_context(expected_columns=["id"], allow_extra_columns=False),
        registry=create_default_quality_registry(),
    )

    assert result.failed is True
    assert store.runs[0]["status"] == "failed"
    assert store.runs[0]["expected"]["allow_extra_columns"] is False
    assert store.runs[0]["params"]["allow_extra_columns"] is True
