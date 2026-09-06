<#
.SYNOPSIS
    Automates Tabular Editor CLI execution to deploy DAX measures into the Power BI semantic model.

.DESCRIPTION
    Discovers Tabular Editor 2 / 3 installations, validates the presence of deploy_measures.cs,
    resolves the target model (offline .pbip Dataset or localhost port), and executes the deployment.

.PARAMETER ModelPath
    Path to the Power BI .pbip dataset folder (e.g., "PowerBI/ModernTradeModel.Dataset") or Analysis Services endpoint/port.

.PARAMETER ScriptPath
    Path to the C# deployment script. Defaults to "scripts/ci/deploy_measures.cs".

.PARAMETER ForceInstall
    Installs Tabular Editor via Chocolatey if not found in PATH or standard installation directories.

.EXAMPLE
    .\scripts\ci\run_measure_deployment.ps1 -ModelPath "PowerBI/ModernTradeModel.Dataset"
#>

[CmdletBinding()]
param (
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$ModelPath = "PowerBI/ModernTradeModel.Dataset",

    [Parameter(Position = 1, Mandatory = $false)]
    [string]$ScriptPath = "scripts/ci/deploy_measures.cs",

    [Parameter(Mandatory = $false)]
    [switch]$ForceInstall
)

$ErrorActionPreference = "Stop"

Write-Host ("=" * 75) -ForegroundColor Cyan
Write-Host "🚀 Tabular Editor Automated DAX Measure Deployment Pipeline" -ForegroundColor Cyan
Write-Host ("=" * 75) -ForegroundColor Cyan

# 1. Resolve Repository Root and Script Paths
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ResolvedScriptPath = Join-Path $RepoRoot $ScriptPath
$ResolvedModelPath = Join-Path $RepoRoot $ModelPath

if (-not (Test-Path $ResolvedScriptPath)) {
    Write-Error "❌ Deployment script not found at path: $ResolvedScriptPath"
    exit 1
}

# 2. Locate Tabular Editor Executable
function Find-TabularEditor {
    # Check PATH first
    $cmd = Get-Command "TabularEditor.exe" -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $cmd3 = Get-Command "TabularEditor3.exe" -ErrorAction SilentlyContinue
    if ($cmd3) { return $cmd3.Source }

    # Check Standard Installation Directories
    $knownPaths = @(
        "C:\Program Files (x86)\Tabular Editor\TabularEditor.exe",
        "C:\Program Files\Tabular Editor 3\TabularEditor3.exe",
        "$env:LOCALAPPDATA\Programs\Tabular Editor\TabularEditor.exe",
        "$env:ChocolateyInstall\bin\TabularEditor.exe",
        "C:\ProgramData\chocolatey\bin\TabularEditor.exe"
    )

    foreach ($path in $knownPaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

$TabularEditorExe = Find-TabularEditor

# 3. Handle Missing Tabular Editor CLI
if (-not $TabularEditorExe) {
    if ($ForceInstall -or ($env:CI -eq "true") -or ($env:GITHUB_ACTIONS -eq "true")) {
        Write-Host "⚠️ Tabular Editor CLI not found. Installing via Chocolatey..." -ForegroundColor Yellow

        if (-not (Get-Command "choco.exe" -ErrorAction SilentlyContinue)) {
            Write-Error "❌ Chocolatey is not installed. Please install Tabular Editor manually or make choco available."
            exit 1
        }

        choco install tabulareditor --yes --no-progress
        $TabularEditorExe = Find-TabularEditor

        if (-not $TabularEditorExe) {
            Write-Error "❌ Tabular Editor installation completed but executable could not be located."
            exit 1
        }
    } else {
        Write-Error "❌ TabularEditor.exe not found in PATH or standard directories. Pass -ForceInstall to install via Chocolatey."
        exit 1
    }
}

Write-Host "✓ Using Tabular Editor CLI: $TabularEditorExe" -ForegroundColor Green
Write-Host "✓ Deployment Script:       $ResolvedScriptPath" -ForegroundColor Gray
Write-Host "✓ Target Model:            $ResolvedModelPath" -ForegroundColor Gray

# 4. Verify Model Target
if (-not (Test-Path $ResolvedModelPath) -and -not ($ModelPath -match "localhost|:\d+")) {
    Write-Warning "⚠️ Model folder not found at '$ResolvedModelPath'. Attempting to locate Model.bim or database.json..."

    $discoveredModel = Get-ChildItem -Path (Join-Path $RepoRoot "PowerBI") -Filter "database.json" -Recurse | Select-Object -First 1
    if ($discoveredModel) {
        $ResolvedModelPath = $discoveredModel.DirectoryName
        Write-Host "✓ Auto-discovered Model Folder: $ResolvedModelPath" -ForegroundColor Green
    } else {
        Write-Error "❌ Could not resolve a valid Power BI Model path. Please check -ModelPath."
        exit 1
    }
}

# 5. Execute Tabular Editor Script
Write-Host "`nExecuting C# batch measure creation..." -ForegroundColor Yellow

$execArgs = @(
    "`"$ResolvedModelPath`"",
    "-S",
    "`"$ResolvedScriptPath`""
)

try {
    $process = Start-Process -FilePath $TabularEditorExe -ArgumentList $execArgs -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -eq 0) {
        Write-Host "`n" + ("=" * 75) -ForegroundColor Green
        Write-Host "✅ MEASURE DEPLOYMENT SUCCEEDED" -ForegroundColor Green
        Write-Host ("=" * 75) -ForegroundColor Green
        exit 0
    } else {
        Write-Error "❌ Tabular Editor exited with error code: $($process.ExitCode)"
        exit $process.ExitCode
    }
} catch {
    Write-Error "❌ An error occurred while executing Tabular Editor: $_"
    exit 1
}
