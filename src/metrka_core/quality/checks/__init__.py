"""Runtime contracts for the built-in quality checks.

Every check receives a :class:`~metrka_core.quality.models.QualityCheckInput`.
Pipeline-owned facts live in ``check_input.context``; declarative YAML values
live separately in ``check_input.params`` and cannot shadow runtime facts. A
missing or malformed required context value raises an exception. The quality
runner records that exception as ``ERROR``; it is never interpreted as a pass.

The core runner currently supplies these gate contexts:

``pre_bronze``
    Run identity (``pipeline_run_id``, ``run_id``), source identity
    (``dataset_id``, ``dataset_file_id``, ``source_capture_id``), selectors
    (``artifact_role``, ``is_zip``, ``file_extension``), and landing facts
    (``landed_file``, ``content_hash``, ``size_bytes``, ``fingerprint_meta``,
    ``storage_zone``, ``landing_path``, ``source_file_name``, and
    ``source_last_modified``).

``post_bronze``
    All ``pre_bronze`` facts plus ``bronze_run_id``, ``bronze_run_path``,
    ``extraction_performed``, ``output_required``, and ``output_files``. When
    ``extraction_performed`` is true, the context also contains
    ``extract_result``, ``requested_extract_count``, and ``safe``.

``pre_silver``
    Run and build identity (``pipeline_run_id``, ``run_id``, ``bronze_run_id``,
    ``silver_run_id``, ``silver_build_id``), source identity (``dataset_id``,
    ``dataset_file_id``, ``source_file_name``), and table facts (``table_key``,
    ``input_file_path``, ``input_format``, ``table``, ``expected_columns``, and
    ``allow_extra_columns``). Extra input columns are allowed at this gate.

``post_silver``
    Run, build, source, and table identity as above, with the transformed
    ``table``, exact ``expected_columns``, ``allow_extra_columns=False``,
    ``output_required``, ``output_files``, ``storage_zone``, and
    ``silver_staging_path``.

These mappings document the built-in version-1.0 implementation. Custom quality
check registration is not a public extension contract in version 1.0; a future
extension API should replace the mappings with typed, gate-specific contexts.
"""

from metrka_core.quality.models import QualityCheckResult, QualityGate, QualityGateResult

__all__ = ["QualityCheckResult", "QualityGate", "QualityGateResult"]
