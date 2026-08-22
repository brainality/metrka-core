"""Execute declarative quality checks at pipeline gates."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any

from metrka_core.quality.models import (
    QualityCheckInput,
    QualityCheckResult,
    QualityConfig,
    QualityGate,
    QualityGateResult,
    QualitySeverity,
    QualityStatus,
)
from metrka_core.quality.registry import QualityRegistry
from metrka_core.quality.store import QualityCheckStore


def run_quality_gate(
    *,
    quality_store: QualityCheckStore,
    config: QualityConfig,
    gate: QualityGate,
    context: dict[str, Any],
    registry: QualityRegistry,
) -> QualityGateResult:
    """Run applicable configured checks for one pipeline gate."""

    specs = config.checks_for_gate(gate)
    registry.validate_specs(specs)

    checks_run = 0
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    error_count = 0
    blocked_count = 0
    failed_check_ids: list[str] = []
    first_error: str | None = None

    for spec in specs:
        if not _matches_context(applies_to=spec.applies_to, context=context):
            continue

        runner = registry.resolve(spec.check_type)

        quality_store.upsert_quality_check_definition(
            {
                "check_id": spec.check_id,
                "check_name": spec.name or spec.check_id,
                "check_type": spec.check_type,
                "layer": spec.gate.layer,
                "target": _target_label(spec.applies_to),
                "severity": spec.severity.value,
                "description": spec.description,
                "code_ref": (f"{runner.__module__}.{runner.__name__}"),
                "default_params": spec.params,
                "is_active": True,
            }
        )

        check_input = QualityCheckInput(
            context=context,
            params=spec.params,
            check_id=spec.check_id,
            quality_gate=gate,
            applies_to=spec.applies_to,
        )

        started = time.perf_counter()

        try:
            result = runner(check_input)

            if result.check_type != spec.check_type:
                raise ValueError(
                    f"Quality runner returned check_type "
                    f"{result.check_type!r}; expected "
                    f"{spec.check_type!r}"
                )

            status = QualityStatus(result.status)

        except Exception as exc:
            status = QualityStatus.ERROR

            result = QualityCheckResult(
                check_type=spec.check_type,
                status=status.value,
                expected={},
                actual={},
                result_summary=(f"{type(exc).__name__}: {exc}"),
                details={"error_type": type(exc).__name__, "error_message": str(exc)},
                params=dict(spec.params),
                duration_ms=None,
            )

        measured_duration_ms = int((time.perf_counter() - started) * 1000)

        if result.duration_ms is None:
            result = replace(result, duration_ms=measured_duration_ms)

        checks_run += 1

        if status is QualityStatus.PASSED:
            passed_count += 1

        elif status is QualityStatus.FAILED:
            failed_count += 1
            failed_check_ids.append(spec.check_id)

        elif status is QualityStatus.ERROR:
            error_count += 1
            failed_check_ids.append(spec.check_id)

        elif status is QualityStatus.SKIPPED:
            skipped_count += 1

        if (
            status in {QualityStatus.FAILED, QualityStatus.ERROR}
            and spec.severity is QualitySeverity.BLOCKING
        ):
            blocked_count += 1

            if first_error is None:
                first_error = result.result_summary

        details = {**result.details, "quality_gate": gate.value, "applies_to": spec.applies_to}

        quality_store.insert_quality_check_run(
            {
                "pipeline_run_id": context.get("pipeline_run_id"),
                "check_id": spec.check_id,
                "dataset_id": context.get("dataset_id"),
                "dataset_file_id": context.get("dataset_file_id"),
                "silver_build_id": context.get("silver_build_id"),
                "run_id": context.get("run_id"),
                "step_id": ("quality_" + spec.check_id.replace(".", "_")),
                "status": status.value,
                "expected": result.expected,
                "actual": result.actual,
                "result_summary": result.result_summary,
                "details": details,
                "params": result.params,
                "duration_ms": result.duration_ms,
            }
        )

    if checks_run == 0:
        return QualityGateResult(
            status=QualityStatus.ERROR.value,
            checks_run=0,
            passed_count=0,
            failed_count=0,
            skipped_count=0,
            blocked_count=1,
            error_count=1,
            failed_check_ids=[],
            error_message=(
                f"Quality gate {gate.value!r} executed no applicable checks. "
                "Check the gate configuration and applies_to selectors."
            ),
            failure_code="QUALITY_GATE_NO_APPLICABLE_CHECKS",
        )

    if checks_run == skipped_count:
        return QualityGateResult(
            status=QualityStatus.ERROR.value,
            checks_run=checks_run,
            passed_count=0,
            failed_count=0,
            skipped_count=skipped_count,
            blocked_count=1,
            error_count=0,
            failed_check_ids=[],
            error_message=(
                f"Quality gate {gate.value!r} completed no checks because every "
                "applicable check was skipped."
            ),
            failure_code="QUALITY_GATE_ALL_CHECKS_SKIPPED",
        )

    gate_status = QualityStatus.FAILED if blocked_count else QualityStatus.PASSED

    return QualityGateResult(
        status=gate_status.value,
        checks_run=checks_run,
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        blocked_count=blocked_count,
        error_count=error_count,
        failed_check_ids=failed_check_ids,
        error_message=first_error,
    )


def _matches_context(*, applies_to: dict[str, Any], context: dict[str, Any]) -> bool:
    """Return whether a check applies to the runtime context."""

    for key, expected in applies_to.items():
        actual = context.get(key)

        if isinstance(expected, list):
            if actual not in expected:
                return False

        elif actual != expected:
            return False

    return True


def _target_label(applies_to: dict[str, Any]) -> str:
    """Build a readable relational target label."""

    if not applies_to:
        return "all"

    return ";".join(f"{key}={_display_value(value)}" for key, value in sorted(applies_to.items()))


def _display_value(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)

    return str(value)
