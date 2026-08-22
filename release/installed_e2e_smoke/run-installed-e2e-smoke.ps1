[CmdletBinding()]
param(
    [string]$CoreRepository = "",
    [string]$ExampleRepository = "",
    [string]$PythonCommand = "python",
    [ValidateSet("portable", "managed")]
    [string]$WorkspacePlacement = "portable",
    [switch]$ResetExampleState,
    [switch]$StopDatabaseAfter
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspaceName = "gapminder"
$datasetId = "gapminder.development"
$environmentVariableNames = @(
    "METRKA_ENV",
    "METRKA_WORKSPACES_CONFIG_PATH",
    "METRKA_METADATA_DSN",
    "METRKA_MIGRATION_DSN",
    "METRKA_METADATA_CONFIG_PATH",
    "METRKA_SILVER_ENGINE_POLICY",
    "METRKA_MIGRATION_OWNER_ROLE",
    "PYTHONPATH"
)
$originalEnvironment = @{}

foreach ($name in $environmentVariableNames) {
    $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

$databaseStarted = $false

function Write-Step {
    param([string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory = ""
    )

    $pushedLocation = $false

    try {
        if ($WorkingDirectory) {
            Push-Location -LiteralPath $WorkingDirectory
            $pushedLocation = $true
        }

        & $FilePath @ArgumentList
        $exitCode = $LASTEXITCODE
    }
    finally {
        if ($pushedLocation) {
            Pop-Location
        }
    }

    if ($exitCode -ne 0) {
        throw "Command failed with exit code ${exitCode}: $FilePath $($ArgumentList -join ' ')"
    }
}

function Get-GitOutput {
    param(
        [string]$Repository,
        [string[]]$ArgumentList
    )

    $output = & git -C $Repository @ArgumentList

    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed in ${Repository}: git $($ArgumentList -join ' ')"
    }

    return @($output)
}

function Assert-CleanMain {
    param(
        [string]$Repository,
        [string]$Label
    )

    $branch = ((Get-GitOutput -Repository $Repository -ArgumentList @("branch", "--show-current")) -join "").Trim()

    if ($branch -ne "main") {
        throw "$Label must be on main. Current branch: $branch"
    }

    $status = @(Get-GitOutput -Repository $Repository -ArgumentList @(
        "status",
        "--porcelain",
        "--untracked-files=normal"
    ))

    if ($status.Count -gt 0) {
        throw "$Label must be clean before the smoke test. Git status: $($status -join '; ')"
    }
}

function Remove-WorkspaceRuntimeDirectory {
    param(
        [string]$WorkspaceRoot,
        [string]$DirectoryName
    )

    $resolvedRoot = [IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    )
    $target = [IO.Path]::GetFullPath((Join-Path $resolvedRoot $DirectoryName))
    $requiredPrefix = $resolvedRoot + [IO.Path]::DirectorySeparatorChar

    if (-not $target.StartsWith($requiredPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the Gapminder workspace: $target"
    }

    if ((Split-Path -Leaf $target) -notin @("data", "logs")) {
        throw "Refusing to remove an unexpected runtime directory: $target"
    }

    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
        Write-Host "Removed disposable runtime directory: $target"
    }
}

function Invoke-PsqlScalar {
    param([string]$Sql)

    Push-Location -LiteralPath $script:resolvedExampleRepository

    try {
        $output = @(
            & docker compose exec -T postgres psql `
                --username postgres `
                --dbname metrka `
                --tuples-only `
                --no-align `
                --quiet `
                --set ON_ERROR_STOP=1 `
                --command $Sql
        )
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        throw "PostgreSQL query failed: $Sql"
    }

    $values = @($output | ForEach-Object { $_.Trim() } | Where-Object { $_ })

    if ($values.Count -ne 1) {
        throw "Expected one scalar value from PostgreSQL, received $($values.Count): $Sql"
    }

    return $values[0]
}

function Assert-DatabaseValue {
    param(
        [string]$Sql,
        [string]$Expected,
        [string]$Description
    )

    $actual = Invoke-PsqlScalar -Sql $Sql

    if ($actual -ne $Expected) {
        throw "$Description. Expected $Expected, received $actual."
    }

    Write-Host "Verified: $Description = $actual"
}

function Assert-FileExists {
    param(
        [string]$Path,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description was not created: $Path"
    }

    Write-Host "Verified: $Description"
}

function Assert-ManagedDefinitionRootUnchanged {
    param(
        [string]$DefinitionRoot,
        [string]$Repository
    )

    foreach ($unexpectedDirectory in @("data", "logs")) {
        $unexpectedPath = Join-Path $DefinitionRoot $unexpectedDirectory
        if (Test-Path -LiteralPath $unexpectedPath) {
            throw "Managed execution wrote runtime state below definition_root: $unexpectedPath"
        }
    }

    Assert-CleanMain `
        -Repository $Repository `
        -Label "metrka-example-datasets after managed execution"
    Write-Host "Verified: managed definition_root remained read-only"
}

try {
    if (-not $ResetExampleState) {
        throw (
            "A full first-run/idempotency smoke requires a fresh disposable example state. " +
            "Run this script with -ResetExampleState. This removes only the " +
            "metrka-example-datasets Compose volume and ignored Gapminder data/logs."
        )
    }

    if ([string]::IsNullOrWhiteSpace($CoreRepository)) {
        $CoreRepository = Join-Path $PSScriptRoot "..\.."
    }

    $resolvedCoreRepository = (Resolve-Path -LiteralPath $CoreRepository).Path

    if ([string]::IsNullOrWhiteSpace($ExampleRepository)) {
        $ExampleRepository = Join-Path `
            (Split-Path -Parent $resolvedCoreRepository) `
            "metrka-example-datasets"
    }

    $script:resolvedExampleRepository = (Resolve-Path -LiteralPath $ExampleRepository).Path
    $definitionRoot = (Resolve-Path -LiteralPath (
        Join-Path $script:resolvedExampleRepository "datasets\gapminder"
    )).Path
    $portableWorkspacesConfigPath = Join-Path `
        $script:resolvedExampleRepository `
        "workspaces.example.yaml"
    $workspacesConfigPath = $portableWorkspacesConfigPath
    $composePath = Join-Path $script:resolvedExampleRepository "compose.yaml"
    $environmentScript = Join-Path $script:resolvedExampleRepository "scripts\set-local-env.ps1"
    $wheelAuditScript = Join-Path $PSScriptRoot "audit_wheel.py"
    $importProbeScript = Join-Path $PSScriptRoot "verify_installed_import.py"
    $versionProbeScript = Join-Path $PSScriptRoot "verify_installed_version.py"
    $roundTripProbeScript = Join-Path $PSScriptRoot "verify_workspace_roundtrip.py"

    foreach ($requiredPath in @(
        $portableWorkspacesConfigPath,
        $composePath,
        $environmentScript,
        $wheelAuditScript,
        $importProbeScript,
        $versionProbeScript,
        $roundTripProbeScript,
        (Join-Path $resolvedCoreRepository "pyproject.toml"),
        (Join-Path $resolvedCoreRepository "src\metrka_core\build_provenance.py")
    )) {
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required smoke-test input is missing: $requiredPath"
        }
    }

    foreach ($commandName in @("git", "docker", $PythonCommand)) {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "Required command is not available: $commandName"
        }
    }

    $bootstrapPython = (Get-Command $PythonCommand).Source

    Write-Step "Checking repositories and prerequisites"
    Assert-CleanMain -Repository $resolvedCoreRepository -Label "metrka-core"
    Assert-CleanMain -Repository $script:resolvedExampleRepository -Label "metrka-example-datasets"
    Invoke-Checked -FilePath $bootstrapPython -ArgumentList @(
        "-c",
        "import sys; assert sys.version_info >= (3, 12), sys.version"
    )
    Invoke-Checked -FilePath "docker" -ArgumentList @("version")
    Invoke-Checked -FilePath "docker" -ArgumentList @("compose", "version")

    $coreCommit = ((Get-GitOutput -Repository $resolvedCoreRepository -ArgumentList @(
        "rev-parse",
        "HEAD"
    )) -join "").Trim()
    $exampleCommit = ((Get-GitOutput -Repository $script:resolvedExampleRepository -ArgumentList @(
        "rev-parse",
        "HEAD"
    )) -join "").Trim()
    Write-Host "Core commit:    $coreCommit"
    Write-Host "Example commit: $exampleCommit"

    $smokeRoot = Join-Path $env:TEMP (
        "metrka-installed-e2e-" + [Guid]::NewGuid().ToString("N")
    )
    $buildEnvironment = Join-Path $smokeRoot "build-venv"
    $installedEnvironment = Join-Path $smokeRoot "installed-venv"
    $wheelDirectory = Join-Path $smokeRoot "wheel"
    $workspaceExportPath = Join-Path $smokeRoot "gapminder-customer-workspace.zip"
    $roundTripRoot = Join-Path $smokeRoot "customer-workspace-roundtrip"
    $roundTripWorkspaceRoot = Join-Path $roundTripRoot $workspaceName
    $roundTripConfigPath = Join-Path $smokeRoot "roundtrip-workspaces.yaml"

    if ($WorkspacePlacement -eq "managed") {
        $dataRoot = Join-Path $smokeRoot "managed-data\gapminder"
        $workspacesConfigPath = Join-Path $smokeRoot "managed-workspaces.yaml"
        New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
        $definitionRootYaml = $definitionRoot.Replace("\", "/")
        $dataRootYaml = $dataRoot.Replace("\", "/")
        $managedWorkspaceConfig = @"
schema_version: 1
workspaces:
  ${workspaceName}:
    placement: managed
    definition_root: "$definitionRootYaml"
    data_root: "$dataRootYaml"
"@
        $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText(
            $workspacesConfigPath,
            $managedWorkspaceConfig,
            $utf8WithoutBom
        )

        $definitionPrefix = $definitionRoot.TrimEnd(
            [IO.Path]::DirectorySeparatorChar,
            [IO.Path]::AltDirectorySeparatorChar
        ) + [IO.Path]::DirectorySeparatorChar
        if ($dataRoot.StartsWith($definitionPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Managed smoke data_root must be outside definition_root"
        }
    }
    else {
        $dataRoot = Join-Path $definitionRoot "data"
    }

    New-Item -ItemType Directory -Path $wheelDirectory -Force | Out-Null

    Write-Step "Building a provenance-bearing wheel from clean main"
    Invoke-Checked -FilePath $bootstrapPython -ArgumentList @("-m", "venv", $buildEnvironment)
    $buildPython = Join-Path $buildEnvironment "Scripts\python.exe"
    Invoke-Checked -FilePath $buildPython -ArgumentList @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        "pip",
        "build"
    )

    [Environment]::SetEnvironmentVariable(
        "PYTHONPATH",
        (Join-Path $resolvedCoreRepository "src"),
        "Process"
    )
    Invoke-Checked -FilePath $buildPython -ArgumentList @(
        "-m",
        "metrka_core.build_provenance",
        "--branch",
        "main"
    ) -WorkingDirectory $resolvedCoreRepository
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $null, "Process")

    Invoke-Checked -FilePath $buildPython -ArgumentList @(
        "-m",
        "build",
        "--wheel",
        "--outdir",
        $wheelDirectory,
        $resolvedCoreRepository
    ) -WorkingDirectory $resolvedCoreRepository

    $wheels = @(Get-ChildItem -LiteralPath $wheelDirectory -Filter "*.whl" -File)

    if ($wheels.Count -ne 1) {
        throw "Expected exactly one wheel, found $($wheels.Count) in $wheelDirectory"
    }

    $wheel = $wheels[0]
    Write-Host "Built wheel: $($wheel.FullName)"

    Invoke-Checked -FilePath $buildPython -ArgumentList @(
        $wheelAuditScript,
        $wheel.FullName
    )

    Write-Step "Installing the wheel into a clean virtual environment"
    Invoke-Checked -FilePath $bootstrapPython -ArgumentList @("-m", "venv", $installedEnvironment)
    $smokePython = Join-Path $installedEnvironment "Scripts\python.exe"
    $smokeMetrka = Join-Path $installedEnvironment "Scripts\metrka.exe"
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        "pip"
    )
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        "-m",
        "pip",
        "install",
        $wheel.FullName,
        "pytest>=8.0"
    )
    Invoke-Checked -FilePath $smokePython -ArgumentList @("-m", "pip", "check")

    if (-not (Test-Path -LiteralPath $smokeMetrka -PathType Leaf)) {
        throw "Installed metrka command was not created: $smokeMetrka"
    }

    Invoke-Checked -FilePath $smokePython -ArgumentList @($importProbeScript) `
        -WorkingDirectory $smokeRoot
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        $versionProbeScript,
        $smokeMetrka,
        $smokeRoot
    ) -WorkingDirectory $smokeRoot
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @("--help") `
        -WorkingDirectory $smokeRoot

    Write-Step "Resetting only the disposable example database and runtime artifacts"
    Write-Warning (
        "Resetting the metrka-example-datasets Compose volume and the ignored " +
        "Gapminder data/logs directories. This operation is not recoverable."
    )
    Invoke-Checked -FilePath "docker" -ArgumentList @(
        "compose",
        "down",
        "--volumes",
        "--remove-orphans"
    ) -WorkingDirectory $script:resolvedExampleRepository
    Remove-WorkspaceRuntimeDirectory -WorkspaceRoot $definitionRoot -DirectoryName "data"
    Remove-WorkspaceRuntimeDirectory -WorkspaceRoot $definitionRoot -DirectoryName "logs"

    Write-Step "Starting the example PostgreSQL service"
    Invoke-Checked -FilePath "docker" -ArgumentList @(
        "compose",
        "up",
        "-d",
        "--wait"
    ) -WorkingDirectory $script:resolvedExampleRepository
    $databaseStarted = $true

    . $environmentScript -UseComposeDatabase
    $env:METRKA_WORKSPACES_CONFIG_PATH = $workspacesConfigPath
    $env:METRKA_SILVER_ENGINE_POLICY = "allow_candidate"
    $env:METRKA_MIGRATION_OWNER_ROLE = "metrka_owner"
    Remove-Item Env:METRKA_METADATA_CONFIG_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue

    foreach ($requiredEnvironmentName in @(
        "METRKA_ENV",
        "METRKA_WORKSPACES_CONFIG_PATH",
        "METRKA_METADATA_DSN",
        "METRKA_MIGRATION_DSN",
        "METRKA_SILVER_ENGINE_POLICY",
        "METRKA_MIGRATION_OWNER_ROLE"
    )) {
        $environmentValue = [Environment]::GetEnvironmentVariable(
            $requiredEnvironmentName,
            "Process"
        )

        if ([string]::IsNullOrWhiteSpace($environmentValue)) {
            throw "Required process environment variable is missing: $requiredEnvironmentName"
        }
    }

    Write-Host "Environment:     $env:METRKA_ENV"
    Write-Host "Workspace placement: $WorkspacePlacement"
    Write-Host "Workspaces config: $env:METRKA_WORKSPACES_CONFIG_PATH"
    Write-Host "Engine policy:   $env:METRKA_SILVER_ENGINE_POLICY"
    Write-Host "Owner role:      $env:METRKA_MIGRATION_OWNER_ROLE"

    Write-Step "Applying and checking PostgreSQL migrations from the installed wheel"
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        "-m",
        "metrka_core.metadata.migrations",
        "upgrade",
        "head"
    ) -WorkingDirectory $script:resolvedExampleRepository
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        "-m",
        "metrka_core.metadata.migrations",
        "check"
    ) -WorkingDirectory $script:resolvedExampleRepository

    Write-Step "Running example repository contract tests against the installed wheel"
    Invoke-Checked -FilePath $smokePython -ArgumentList @(
        "-m",
        "pytest",
        (Join-Path $script:resolvedExampleRepository "tests"),
        "-q"
    ) -WorkingDirectory $smokeRoot

    Write-Step "Validating the Gapminder workspace without PostgreSQL execution"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "workspace",
        "validate",
        $workspaceName,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot

    Write-Step "Running Gapminder for the first time"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "run",
        $workspaceName,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot

    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM logs.pipeline_runs WHERE workspace_name = 'gapminder' AND status = 'success';" `
        -Expected "1" `
        -Description "successful pipeline runs after first execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM meta.marshaled_files WHERE dataset_id = 'gapminder.development';" `
        -Expected "1" `
        -Description "registered Bronze source files after first execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM logs.silver_build_attempts WHERE dataset_id = 'gapminder.development' AND status = 'succeeded';" `
        -Expected "1" `
        -Description "successful Silver builds after first execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publication_candidates WHERE dataset_id = 'gapminder.development' AND status = 'awaiting_approval';" `
        -Expected "1" `
        -Description "publication candidates awaiting approval"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publications WHERE dataset_id = 'gapminder.development';" `
        -Expected "0" `
        -Description "publications before operator approval"

    $bronzeFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $dataRoot "files\bronze\runs") `
            -Recurse -File -ErrorAction Stop
    )
    $silverCsvFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $dataRoot "files\silver\tables") `
            -Recurse -Filter "*.csv" -File -ErrorAction Stop
    )
    $silverParquetFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $dataRoot "files\silver\tables") `
            -Recurse -Filter "*.parquet" -File -ErrorAction Stop
    )
    $manifestFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $dataRoot "files\silver\manifests") `
            -Recurse -Filter "*.json" -File -ErrorAction Stop
    )

    if ($bronzeFiles.Count -lt 1) {
        throw "The first run produced no Bronze files."
    }

    if ($silverCsvFiles.Count -lt 1 -or $silverParquetFiles.Count -lt 1) {
        throw "The first run did not produce both CSV and Parquet Silver files."
    }

    if ($manifestFiles.Count -lt 1) {
        throw "The first run produced no Silver manifest."
    }

    Write-Host "Verified: Bronze files = $($bronzeFiles.Count)"
    Write-Host "Verified: Silver CSV files = $($silverCsvFiles.Count)"
    Write-Host "Verified: Silver Parquet files = $($silverParquetFiles.Count)"
    Write-Host "Verified: Silver manifests = $($manifestFiles.Count)"

    Write-Step "Approving and publishing through the installed operations CLI"
    $candidateId = Invoke-PsqlScalar -Sql (
        "SELECT candidate_id FROM catalog.dataset_publication_candidates " +
        "WHERE dataset_id = 'gapminder.development' AND status = 'awaiting_approval' " +
        "ORDER BY requested_at DESC LIMIT 1;"
    )
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "operations",
        "publication-candidates",
        "approve",
        $candidateId,
        "--approved-by",
        "installed-e2e-smoke"
    ) -WorkingDirectory $smokeRoot
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "operations",
        "publication-candidates",
        "publish",
        $candidateId,
        "--workspace",
        $workspaceName,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot

    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publication_candidates WHERE candidate_id = '$candidateId' AND status = 'published';" `
        -Expected "1" `
        -Description "published candidate rows"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publications WHERE dataset_id = 'gapminder.development' AND is_current IS TRUE;" `
        -Expected "1" `
        -Description "current Gapminder publications"

    $publicationId = Invoke-PsqlScalar -Sql (
        "SELECT publication_id FROM catalog.dataset_publications " +
        "WHERE dataset_id = 'gapminder.development' AND is_current IS TRUE;"
    )
    $pointerPath = Join-Path $dataRoot (
        "current\latest\silver\dataset--gapminder.development.json"
    )
    $latestViewPath = Join-Path $dataRoot (
        "files\silver\views\gapminder\publication=$publicationId\latest.sql"
    )
    $historyViewPath = Join-Path $dataRoot (
        "files\silver\views\gapminder\history.sql"
    )
    Assert-FileExists -Path $pointerPath -Description "current Silver pointer"
    Assert-FileExists -Path $latestViewPath -Description "publication-versioned latest view"
    Assert-FileExists -Path $historyViewPath -Description "Silver history view"

    $pointer = Get-Content -LiteralPath $pointerPath -Raw | ConvertFrom-Json

    if ($pointer.publication_id -ne $publicationId) {
        throw (
            "Current pointer publication mismatch. Expected $publicationId, " +
            "received $($pointer.publication_id)."
        )
    }

    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "operations",
        "reconcile-publications",
        "--workspace",
        $workspaceName,
        "--dataset-id",
        $datasetId,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot

    Write-Step "Running Gapminder a second time to prove idempotency"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "run",
        $workspaceName,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot

    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM logs.pipeline_runs WHERE workspace_name = 'gapminder' AND status = 'success';" `
        -Expected "2" `
        -Description "successful pipeline runs after repeated execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM logs.pipeline_runs WHERE workspace_name = 'gapminder' AND status <> 'success';" `
        -Expected "0" `
        -Description "non-successful pipeline runs"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM meta.marshaled_files WHERE dataset_id = 'gapminder.development';" `
        -Expected "1" `
        -Description "Bronze source records after repeated execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM logs.silver_build_attempts WHERE dataset_id = 'gapminder.development';" `
        -Expected "1" `
        -Description "Silver build attempts after repeated execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publication_candidates WHERE dataset_id = 'gapminder.development';" `
        -Expected "1" `
        -Description "publication candidates after repeated execution"
    Assert-DatabaseValue `
        -Sql "SELECT count(*) FROM catalog.dataset_publications WHERE dataset_id = 'gapminder.development';" `
        -Expected "1" `
        -Description "publications after repeated execution"

    if ($WorkspacePlacement -eq "managed") {
        Assert-ManagedDefinitionRootUnchanged `
            -DefinitionRoot $definitionRoot `
            -Repository $script:resolvedExampleRepository
    }

    Write-Step "Exporting and verifying a customer workspace package"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "workspace",
        "export",
        $workspaceName,
        "--output",
        $workspaceExportPath,
        "--workspaces-config-path",
        $workspacesConfigPath
    ) -WorkingDirectory $smokeRoot
    Assert-FileExists -Path $workspaceExportPath -Description "customer workspace export"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "workspace",
        "verify-export",
        $workspaceExportPath
    ) -WorkingDirectory $smokeRoot

    Write-Step "Reopening the customer export as an independent portable workspace"
    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "workspace",
        "import",
        $workspaceExportPath,
        "--destination-directory",
        $roundTripRoot,
        "--workspaces-config-path",
        $roundTripConfigPath
    ) -WorkingDirectory $smokeRoot
    Assert-FileExists `
        -Path (Join-Path $roundTripWorkspaceRoot "metrka-workspace-manifest.json") `
        -Description "extracted customer workspace manifest"

    Invoke-Checked -FilePath $smokeMetrka -ArgumentList @(
        "workspace",
        "validate",
        $workspaceName,
        "--workspaces-config-path",
        $roundTripConfigPath
    ) -WorkingDirectory $smokeRoot
    $roundTripProbeArguments = @(
        $roundTripProbeScript,
        $roundTripWorkspaceRoot,
        "--workspace-name",
        $workspaceName,
        "--dataset-id",
        $datasetId
    )
    foreach ($sourceRoot in @($definitionRoot, $dataRoot)) {
        $roundTripProbeArguments += @("--forbidden-source-root", $sourceRoot)
    }
    Invoke-Checked -FilePath $smokePython -ArgumentList $roundTripProbeArguments `
        -WorkingDirectory $smokeRoot

    if ($WorkspacePlacement -eq "managed") {
        Assert-ManagedDefinitionRootUnchanged `
            -DefinitionRoot $definitionRoot `
            -Repository $script:resolvedExampleRepository
    }

    Write-Step "Installed end-to-end smoke passed (placement=$WorkspacePlacement)"
    Write-Host "Wheel:          $($wheel.FullName)"
    Write-Host "Installed venv: $installedEnvironment"
    Write-Host "Publication:    $publicationId"
    Write-Host "Placement:      $WorkspacePlacement"
    Write-Host "Definition root: $definitionRoot"
    Write-Host "Data root:      $dataRoot"
    Write-Host "Customer export: $workspaceExportPath"
    Write-Host "Round-trip workspace: $roundTripWorkspaceRoot"
    Write-Host "Database:       Docker Compose PostgreSQL on port 55432"

    if (-not $StopDatabaseAfter) {
        Write-Host "Database was left running for inspection. Stop it with:"
        Write-Host "  docker compose -f `"$composePath`" down"
    }
}
finally {
    if ($StopDatabaseAfter -and $databaseStarted) {
        try {
            Invoke-Checked -FilePath "docker" -ArgumentList @("compose", "down") `
                -WorkingDirectory $script:resolvedExampleRepository
        }
        catch {
            Write-Warning "Could not stop the example database: $($_.Exception.Message)"
        }
    }

    foreach ($name in $environmentVariableNames) {
        [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], "Process")
    }
}
