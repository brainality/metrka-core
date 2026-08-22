"""Small runtime identity passed to pipeline actions."""

from __future__ import annotations

from dataclasses import dataclass

from metrka_core.pipeline.provenance import CodeProvenance


@dataclass(frozen=True)
class ActionRuntime:
    """
    Runtime identity shared by pipeline actions.

    This object deliberately contains no persistence or storage
    dependencies.
    """

    pipeline_run_id: str
    dataset_name: str
    code_provenance: CodeProvenance
