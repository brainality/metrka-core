"""Load and validate declarative data-quality configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from metrka_core.quality.models import QualityCheckSpec, QualityConfig, QualityGate, QualitySeverity

_ROOT_KEYS = frozenset({"version", "gates"})

_CHECK_KEYS = frozenset({"id", "type", "severity", "name", "description", "applies_to", "params"})

_APPLIES_TO_KEYS_BY_GATE: dict[QualityGate, frozenset[str]] = {
    QualityGate.PRE_BRONZE: frozenset(
        {
            "artifact_role",
            "dataset_id",
            "file_extension",
            "is_zip",
            "source_file_name",
            "storage_zone",
        }
    ),
    QualityGate.POST_BRONZE: frozenset(
        {
            "artifact_role",
            "dataset_id",
            "extraction_performed",
            "file_extension",
            "is_zip",
            "output_required",
            "source_file_name",
            "storage_zone",
        }
    ),
    QualityGate.PRE_SILVER: frozenset(
        {"dataset_id", "input_format", "source_file_name", "table_key"}
    ),
    QualityGate.POST_SILVER: frozenset(
        {"dataset_id", "source_file_name", "storage_zone", "table_key"}
    ),
}


def load_quality_config(path: Path) -> QualityConfig:
    """Load and validate one quality YAML file."""

    if not path.exists():
        raise FileNotFoundError(f"Quality config does not exist: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid quality YAML: {path}") from exc

    return parse_quality_config(raw, source=str(path))


def parse_quality_config(raw: object, *, source: str = "<memory>") -> QualityConfig:
    """Validate an already parsed quality configuration."""

    if not isinstance(raw, dict):
        raise ValueError(f"Quality config root must be a mapping: {source}")

    unexpected_root_keys = set(raw) - _ROOT_KEYS

    if unexpected_root_keys:
        raise ValueError(
            f"Unsupported quality config fields in {source}: {sorted(unexpected_root_keys)}"
        )

    version = raw.get("version")

    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ValueError(f"Quality config version must be integer 1: {source}")

    gates = raw.get("gates")

    if not isinstance(gates, dict):
        raise ValueError(f"Quality config gates must be a mapping: {source}")

    checks: list[QualityCheckSpec] = []
    known_check_ids: set[str] = set()
    configured_gates: set[QualityGate] = set()

    for gate_name, raw_checks in gates.items():
        if not isinstance(gate_name, str):
            raise ValueError(f"Quality gate name must be a string: {source}")

        try:
            gate = QualityGate(gate_name)
        except ValueError as exc:
            supported = [item.value for item in QualityGate]

            raise ValueError(
                f"Unsupported quality gate {gate_name!r} in {source}; supported gates: {supported}"
            ) from exc

        configured_gates.add(gate)

        if not isinstance(raw_checks, list):
            raise ValueError(f"Quality gate {gate_name!r} must contain a list of checks: {source}")

        if not raw_checks:
            raise ValueError(
                f"Quality gate {gate_name!r} must contain at least one check: {source}"
            )

        for index, raw_check in enumerate(raw_checks):
            location = f"{source}:gates.{gate_name}[{index}]"

            if not isinstance(raw_check, dict):
                raise ValueError(f"Quality check must be a mapping: {location}")

            unexpected_check_keys = set(raw_check) - _CHECK_KEYS

            if unexpected_check_keys:
                raise ValueError(
                    f"Unsupported quality check fields at "
                    f"{location}: "
                    f"{sorted(unexpected_check_keys)}"
                )

            check_id = _required_string(raw_check, "id", location)
            check_type = _required_string(raw_check, "type", location)
            severity_value = _required_string(raw_check, "severity", location)

            if check_id in known_check_ids:
                raise ValueError(f"Duplicate quality check id {check_id!r}: {source}")

            known_check_ids.add(check_id)

            try:
                severity = QualitySeverity(severity_value)
            except ValueError as exc:
                supported = [item.value for item in QualitySeverity]

                raise ValueError(
                    f"Unsupported severity "
                    f"{severity_value!r} at {location}; "
                    f"supported values: {supported}"
                ) from exc

            applies_to = _optional_mapping(raw_check, "applies_to", location)
            _validate_applies_to(applies_to=applies_to, gate=gate, location=location)
            params = _optional_mapping(raw_check, "params", location)

            checks.append(
                QualityCheckSpec(
                    check_id=check_id,
                    check_type=check_type,
                    gate=gate,
                    severity=severity,
                    name=_optional_string(raw_check, "name", location),
                    description=_optional_string(raw_check, "description", location),
                    applies_to=applies_to,
                    params=params,
                )
            )

    missing_gates = set(QualityGate) - configured_gates

    if missing_gates:
        raise ValueError(
            f"Quality config must define every gate in {source}; "
            f"missing gates: {sorted(gate.value for gate in missing_gates)}"
        )

    return QualityConfig(version=version, checks=tuple(checks))


def _validate_applies_to(*, applies_to: dict[str, Any], gate: QualityGate, location: str) -> None:
    allowed_keys = _APPLIES_TO_KEYS_BY_GATE[gate]
    unsupported_keys = set(applies_to) - allowed_keys

    if unsupported_keys:
        raise ValueError(
            f"Unsupported applies_to fields at {location}: {sorted(unsupported_keys)}; "
            f"supported fields for {gate.value}: {sorted(allowed_keys)}"
        )

    for key, value in applies_to.items():
        if isinstance(value, list):
            if not value:
                raise ValueError(f"applies_to.{key} must not be an empty list: {location}")

            if not all(_is_selector_scalar(item) for item in value):
                raise ValueError(
                    f"applies_to.{key} list items must be strings, numbers, or booleans: {location}"
                )

        elif not _is_selector_scalar(value):
            raise ValueError(
                f"applies_to.{key} must be a string, number, boolean, or list: {location}"
            )


def _is_selector_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool))


def _required_string(mapping: dict[str, Any], key: str, location: str) -> str:
    value = mapping.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Quality check field {key!r} must be a non-empty string: {location}")

    return value.strip()


def _optional_string(mapping: dict[str, Any], key: str, location: str) -> str | None:
    value = mapping.get(key)

    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Quality check field {key!r} must be a non-empty string or null: {location}"
        )

    return value.strip()


def _optional_mapping(mapping: dict[str, Any], key: str, location: str) -> dict[str, Any]:
    if key not in mapping:
        return {}

    value = mapping[key]

    if not isinstance(value, dict):
        raise ValueError(f"Quality check field {key!r} must be a mapping: {location}")

    return dict(value)
