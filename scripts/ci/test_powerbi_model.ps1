# ==============================================================================
# test_powerbi_model.ps1
# Headless Power BI, Watch Folder & Tabular Editor CI Validation Harness
# ==============================================================================
[CmdletBinding()]
param (
    [string]$RepoRoot = (Get-Location).Path,
    [string]$ModelPath = "PowerBI/model.bim",
    [string]$BPARulesPath = "PowerBI/CI/bpa_rules.json",
    [string]$TabularEditorPath = "C:\Program Files (x86)\Tabular Editor\TabularEditor.exe",
    # When set (the Windows CI gate sets it), a missing model, a missing Tabular Editor or a failed compile is a FAILURE.
    # Without it the compile step reports SKIPPED so the script still runs on machines without Tabular Editor.
    [switch]$RequireModelCompile
)

$ErrorActionPreference = "Stop"
$failures = @()

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🚀 Starting Power BI CI & Tabular Editor Harness (Windows)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# STEP 1: Watch Folder CSV Schema & Row Volume Validation
# ------------------------------------------------------------------------------
Write-Host "`n[1/4] Validating Watch Folders & Data Integrity..." -ForegroundColor Yellow

$watchFiles = @(
    @{
        Path = "PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Aug_2026.csv"
        MinRows = 40000
        RequiredCols = @("Source_Month", "Distributor", "Chain", "Brand", "EAN", "NSV_Lakh", "Chain_TOT_Pct")
    },
    @{
        Path = "PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv"
        MinRows = 2000
        RequiredCols = @("Source_Month", "Chain Name", "Brand", "EAN Code", "ME_Contribution_Pct")
    },
    @{
        Path = "PowerBI/RawDataFolders/ClaimMaster_Quarterly/claim_master_chain_AprJun_2026.csv"
        MinRows = 10
        RequiredCols = @("Entity", "Amount_Lakh")
    }
)

foreach ($item in $watchFiles) {
    $fullPath = Join-Path $RepoRoot $item.Path
    if (-not (Test-Path $fullPath)) {
        # Write-Host "  ⚠ Optional: $($item.Path) (not yet committed)" -ForegroundColor Yellow
        continue
    }

    $csvData = Import-Csv -Path $fullPath
    $rowCount = $csvData.Count
    Write-Host "  ✓ Found: $($item.Path) (Rows: $rowCount)" -ForegroundColor Green

    if ($rowCount -lt $item.MinRows) {
        $failures += "Row count check failed for $($item.Path): Found $rowCount, expected >= $($item.MinRows)"
        Write-Host "    ❌ Row count too low: $rowCount < $($item.MinRows)" -ForegroundColor Red
    }

    if ($rowCount -gt 0) {
        $firstRowCols = $csvData[0].PSObject.Properties.Name
        foreach ($col in $item.RequiredCols) {
            if ($firstRowCols -notcontains $col) {
                $failures += "Schema drift in $($item.Path): Missing required column '$col'"
                Write-Host "    ❌ Missing Column: $col" -ForegroundColor Red
            }
        }
    }
}

# ------------------------------------------------------------------------------
# STEP 2: Raw DAX & Power Query File Sanity Checks
# ------------------------------------------------------------------------------
Write-Host "`n[2/4] Validating Raw DAX & Power Query Files..." -ForegroundColor Yellow

$daxFiles = Get-ChildItem -Path (Join-Path $RepoRoot "PowerBI/DAX") -Filter "*.dax" -Recurse -ErrorAction SilentlyContinue
if ($daxFiles.Count -gt 0) {
    foreach ($daxFile in $daxFiles) {
        $content = Get-Content -Path $daxFile.FullName -Raw
        $openParen = ($content.ToCharArray() | Where-Object { $_ -eq '(' }).Count
        $closeParen = ($content.ToCharArray() | Where-Object { $_ -eq ')' }).Count

        if ($openParen -ne $closeParen) {
            $failures += "DAX Bracket mismatch in $($daxFile.Name)"
            Write-Host "  ❌ $($daxFile.Name): Parenthesis mismatch ($openParen vs $closeParen)" -ForegroundColor Red
        } else {
            Write-Host "  ✓ Raw DAX syntax balanced: $($daxFile.Name)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ℹ No .dax files found in PowerBI/DAX" -ForegroundColor Gray
}

$pqFiles = Get-ChildItem -Path (Join-Path $RepoRoot "PowerBI/PowerQuery") -Filter "*.pq" -Recurse -ErrorAction SilentlyContinue
if ($pqFiles.Count -gt 0) {
    foreach ($pqFile in $pqFiles) {
        $content = Get-Content -Path $pqFile.FullName -Raw
        # A Power Query parameter (e.g. 00_Parameters.pq) is a value tagged
        # `meta [IsParameterQuery=true, ...]` -- valid M with no let/in.
        $isParameterQuery = $content -match 'meta\s*\[\s*IsParameterQuery\s*=\s*true'
        if ($isParameterQuery -or ($content -match "let" -and $content -match "in")) {
            Write-Host "  ✓ Structural M-code valid: $($pqFile.Name)" -ForegroundColor Green
        } else {
            $failures += "Power Query structural error in $($pqFile.Name): Missing 'let' or 'in' clause"
            Write-Host "  ❌ $($pqFile.Name): Malformed M-code structure" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  ℹ No .pq files found in PowerBI/PowerQuery" -ForegroundColor Gray
}

# ------------------------------------------------------------------------------
# STEP 3: Tabular Editor CLI -- load the model and save it again (the model "compiles")
# ------------------------------------------------------------------------------
# What this proves: Tabular Editor can deserialise PowerBI/model.bim into a tabular model (every property valid
# for the compatibility level) and write it back with the same tables and measures.
# What it does NOT prove: that DAX measures return the right numbers. That needs Power BI Desktop.
Write-Host "`n[3/4] Running Tabular Editor Model Compilation (load + save)..." -ForegroundColor Yellow

$fullModelPath = Join-Path $RepoRoot $ModelPath
$fullBPARulesPath = Join-Path $RepoRoot $BPARulesPath
$compileStatus = "SKIPPED"

function Skip-Or-Fail([string]$reason) {
    if ($RequireModelCompile) {
        $script:failures += "Model compilation not performed: $reason"
        Write-Host "  ❌ $reason (compilation is required)" -ForegroundColor Red
        $script:compileStatus = "FAILED"
    } else {
        Write-Host "  ⚠ SKIPPED: $reason (use -RequireModelCompile to make this a failure)" -ForegroundColor Yellow
    }
}

if (-not (Test-Path $fullModelPath)) {
    Skip-Or-Fail "semantic model not found at $ModelPath"
} else {
    Write-Host "  ✓ Found semantic model: $ModelPath" -ForegroundColor Green
    $teCmd = $null
    if ($env:TE_PATH -and (Test-Path $env:TE_PATH)) { $teCmd = $env:TE_PATH }
    elseif (Test-Path $TabularEditorPath) { $teCmd = $TabularEditorPath }
    else {
        $found = Get-Command "TabularEditor.exe" -ErrorAction SilentlyContinue
        if ($found) { $teCmd = $found.Source }
    }

    if (-not $teCmd) {
        Skip-Or-Fail "Tabular Editor CLI is not installed"
    } else {
        Write-Host "  ✓ Tabular Editor CLI: $teCmd" -ForegroundColor Green
        $outBim = Join-Path ([System.IO.Path]::GetTempPath()) ("compiled_model_" + [guid]::NewGuid().ToString("N") + ".bim")
        $proc = Start-Process -FilePath $teCmd -ArgumentList @("`"$fullModelPath`"", "-B", "`"$outBim`"") -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0 -or -not (Test-Path $outBim)) {
            $failures += "Tabular Editor could not load and save $ModelPath (exit code $($proc.ExitCode))"
            Write-Host "  ❌ Tabular Editor failed on $ModelPath (exit code $($proc.ExitCode))" -ForegroundColor Red
            $compileStatus = "FAILED"
        } else {
            $inModel  = (Get-Content $fullModelPath -Raw | ConvertFrom-Json).model
            $outRaw   = Get-Content $outBim -Raw | ConvertFrom-Json
            $outModel = if ($outRaw.model) { $outRaw.model } else { $outRaw }
            # A table with no "measures" key must count as 0 (in PowerShell @($null).Count is 1, which inflated the saved model's count).
            $countMeasures = { param($tables) ($tables | ForEach-Object { if ($_.measures) { @($_.measures).Count } else { 0 } } | Measure-Object -Sum).Sum }
            $inMeasures  = & $countMeasures $inModel.tables
            $outMeasures = & $countMeasures $outModel.tables
            Write-Host "  ✓ Saved by Tabular Editor: tables $(@($outModel.tables).Count) (source $(@($inModel.tables).Count)), measures $outMeasures (source $inMeasures)" -ForegroundColor Green
            if (@($outModel.tables).Count -ne @($inModel.tables).Count -or $outMeasures -ne $inMeasures) {
                $failures += "Tabular Editor round trip changed the model: tables $(@($inModel.tables).Count)->$(@($outModel.tables).Count), measures $inMeasures->$outMeasures"
                Write-Host "  ❌ Round trip changed the table or measure count" -ForegroundColor Red
                $compileStatus = "FAILED"
            } else {
                $compileStatus = "PASSED"
            }
        }
    }
}

# ------------------------------------------------------------------------------
# STEP 4: Best Practice Analyzer (BPA) rules -- is the rule file runnable?
# ------------------------------------------------------------------------------
# Tabular Editor's BPA only runs rules that have an "Expression". The rule file in this repo is documentation-style
# (ID / Name / Severity / Description) with no Expression, so BPA is reported as NOT EXECUTED, never as passed.
Write-Host "`n[4/4] Checking Best Practice Analyzer rules..." -ForegroundColor Yellow
$bpaStatus = "NOT_EXECUTED"
if (Test-Path $fullBPARulesPath) {
    $rules = @(Get-Content $fullBPARulesPath -Raw | ConvertFrom-Json)
    $runnable = @($rules | Where-Object { $_.Expression }).Count
    Write-Host "  ℹ BPA rules: $($rules.Count) in $BPARulesPath, $runnable with an Expression (runnable by Tabular Editor)" -ForegroundColor Gray
    if ($runnable -gt 0 -and $runnable -eq $rules.Count) { $bpaStatus = "RUNNABLE_NOT_RUN" }
    Write-Host "  ⚠ BPA status: $bpaStatus - these rules are not executed by this script" -ForegroundColor Yellow
} else {
    Write-Host "  ℹ BPA rules file not found at $BPARulesPath" -ForegroundColor Gray
}

Write-Host "`n  VALIDATION SCOPE" -ForegroundColor Cyan
Write-Host "    raw DAX / Power Query text checks : run (static: brackets and let/in only)" -ForegroundColor Cyan
Write-Host "    model compile (Tabular Editor)    : $compileStatus" -ForegroundColor Cyan
Write-Host "    BPA rules                         : $bpaStatus" -ForegroundColor Cyan
Write-Host "    DAX results / measure values      : NOT CHECKED (needs Power BI Desktop)" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# Final Verdict
# ------------------------------------------------------------------------------
Write-Host "`n==========================================================" -ForegroundColor Cyan
if ($failures.Count -gt 0) {
    Write-Host " ❌ CI RUN FAILED WITH $($failures.Count) ERROR(S):" -ForegroundColor Red
    foreach ($err in $failures) {
        Write-Host "   • $err" -ForegroundColor Red
    }
    Write-Host "==========================================================" -ForegroundColor Cyan
    exit 1
} else {
    Write-Host " ✅ CHECKS PASSED (see VALIDATION SCOPE above for what was and was not run)" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    exit 0
}
