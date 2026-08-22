# Changelog

All notable changes to `metrka-core` are documented in this file.

The project follows [Semantic Versioning](https://semver.org/). Internal
modules remain implementation details unless they are listed in
`PUBLIC_API.md`.

## [1.0.0] - 2026-08-22

First public release.

### Added

- A stable `metrka_core.api` surface for running configured pipelines and
  initializing dataset workspaces.
- The `metrka run` command and the equivalent `python -m metrka_core run`
  invocation.
- Stable `metrka operations` commands for metadata migrations, Silver engine
  decisions, publication candidates, and publication reconciliation.
- `metrka workspace init` for creating and registering a Bronze-ready HTTP
  dataset workspace.
- Read-only `validate_workspace()` and `metrka workspace validate` entry points
  for checking workspace, pipeline, quality, and Silver contract configuration
  without PostgreSQL or pipeline execution.
- `export_workspace()`, `verify_workspace_export()`, and matching
  `metrka workspace` commands for assembling detached definition and data roots
  as one portable, manifest-verified customer package.
- A fail-closed customer-export content policy with structured
  `WorkspaceExportContentPolicyError` and `WorkspaceExportPolicyViolation`
  evidence for sensitive or deployment-only definition files.
- PostgreSQL-backed metadata, catalog, lineage, quality, publication, and
  audit stores with Alembic migrations.
- Configurable acquisition, Bronze, documentation, and governed Silver
  processing.
- Immutable source captures, file integrity verification, transformation
  evidence, canonical fingerprints, and publication reconciliation.
- Typed extension contracts for custom actions, acquisition adapters, and
  source-schema integrations.
- Deterministic runtime service injection for clocks and identifiers.
- Portable code provenance for both source checkouts and installed
  `metrka-core` wheels.
- Apache-2.0 licensing recorded in PEP 639 package metadata and included in
  source and wheel distributions.

### Operational requirements

- Python 3.12 or newer.
- PostgreSQL with the current metadata migrations applied.
- Workspace definitions stored in Git and selected through explicit portable
  or managed placement configuration in `workspaces.local.yaml`.
- Production wheels must contain the generated `_build_provenance.json`
  package resource.

[1.0.0]: https://github.com/brainality/metrka-core/releases/tag/v1.0.0
