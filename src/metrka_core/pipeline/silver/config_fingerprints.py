"""Fingerprints for configuration affecting Silver builds."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from metrka_core.quality.models import QualityConfig


def calculate_quality_config_hash(config: QualityConfig) -> str:
    payload = {
        "version": config.version,
        "checks": [
            {
                "check_id": check.check_id,
                "check_type": check.check_type,
                "gate": check.gate.value,
                "severity": check.severity.value,
                "name": check.name,
                "description": check.description,
                "applies_to": check.applies_to,
                "params": check.params,
            }
            for check in config.checks
        ],
    }

    return calculate_config_hash(payload)


def calculate_config_hash(payload: object) -> str:
    normalized = _normalize(payload)

    canonical_json = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _normalize(value: object) -> object:
    if value is None:
        return None

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return value.as_posix()

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }

    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]

    if isinstance(value, (str, int, float, bool)):
        return value

    raise TypeError(f"Unsupported configuration fingerprint type: {type(value).__name__}")
