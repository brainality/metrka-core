# Installed Metrka end-to-end smoke

This smoke test proves that the built `metrka-core` wheel works without importing
`metrka_core` from the source checkout. It uses the public `metrka` command, the
public Gapminder example workspace, and a fresh PostgreSQL database.

## Preconditions

- `metrka-core` is on a clean local `main` branch.
- `metrka-example-datasets` is on a clean local `main` branch.
- Python 3.12 or newer is available as `python`.
- Docker Desktop is running and Linux containers are enabled.
- Internet access is available for Python dependencies, the PostgreSQL image,
  and the pinned Gapminder source file.

The script and its four Python audit helpers create isolated build and
installation virtual environments below `$env:TEMP`. It does not use the
active development virtual environment. The helpers are separate files so
the checks work in both Windows PowerShell 5.1 and PowerShell 7 without the
legacy quoting problems of multiline `python -c` commands.

## Run

```powershell
& .\release\installed_e2e_smoke\run-installed-e2e-smoke.ps1 -ResetExampleState
```

Use `-StopDatabaseAfter` if PostgreSQL should be stopped after the test:

```powershell
& .\release\installed_e2e_smoke\run-installed-e2e-smoke.ps1 `
    -ResetExampleState `
    -StopDatabaseAfter
```

The default run exercises a portable source workspace. Run the identical
installed workflow with definitions and data on separate roots using:

```powershell
& .\release\installed_e2e_smoke\run-installed-e2e-smoke.ps1 `
    -WorkspacePlacement managed `
    -ResetExampleState `
    -StopDatabaseAfter
```

The managed run creates its placement registry and `data_root` below the
isolated smoke directory. The tracked Gapminder directory remains the
`definition_root`; any `data` and `logs` directories there are removed before
the run and must remain absent afterward.

By default, the script resolves `metrka-core` from its own repository location
and expects `metrka-example-datasets` beside it. Custom locations can be
supplied explicitly:

```powershell
& .\release\installed_e2e_smoke\run-installed-e2e-smoke.ps1 `
    -CoreRepository "C:\path\to\metrka-core" `
    -ExampleRepository "C:\path\to\metrka-example-datasets" `
    -ResetExampleState
```

## Disposable state warning

`-ResetExampleState` is required because the smoke test proves first-run and
second-run behavior from an empty state. It permanently removes only:

- the Docker Compose volume declared by `metrka-example-datasets/compose.yaml`;
- `metrka-example-datasets/datasets/gapminder/data`;
- `metrka-example-datasets/datasets/gapminder/logs`.

The two workspace directories are ignored runtime outputs. Tracked source and
configuration files are not removed.

## What is verified

1. Both repositories are clean and on `main`.
2. Build provenance is generated from the clean `metrka-core` checkout.
3. A wheel is built and audited for provenance, Apache-2.0 metadata, the exact
   non-empty license text, and excluded scratch modules.
4. The wheel is installed in a clean virtual environment.
5. `metrka_core` resolves from `site-packages`, not the source checkout.
6. PostgreSQL starts from the example repository and all migrations pass.
7. Example repository tests pass against the installed wheel.
8. `metrka workspace validate gapminder` succeeds.
9. The first `metrka run gapminder` creates Bronze and Silver state.
10. The initial publication candidate is approved and published through the
    installed operations CLI.
11. Current and history projections exist and reconciliation succeeds.
12. A second run is idempotent: it creates another successful pipeline receipt
    but no additional marshaled file, Silver build, candidate, or publication.
13. The customer workspace ZIP passes independent manifest, membership, path,
    size, and checksum verification.
14. `metrka workspace import` verifies the ZIP again, extracts it below a new
    root, and registers the reopened portable workspace using only the installed
    CLI.
15. Extracted contract definitions, contract snapshots, Silver manifests,
    latest pointers, SQL views, CSV, and Parquet files resolve from their new
    roots. Recorded checksums and table shapes still match, and no text artifact
    contains the original workspace's absolute path.
16. With `-WorkspacePlacement managed`, Bronze, Silver, receipts, snapshots,
    manifests, pointers, and views are created below the detached `data_root`.
    The Git-backed `definition_root` remains clean and contains no runtime
    `data` or `logs` directory.

Successful completion ends with `Installed end-to-end smoke passed` and the
tested placement in parentheses.
