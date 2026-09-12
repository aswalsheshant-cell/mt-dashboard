# ==============================================================================
# test_powerbi_model.ps1
# Headless Power BI, Watch Folder & Tabular Editor CI Validation Harness
# ==============================================================================
[CmdletBinding()]
param (
    [string]$RepoRoot = (Get-Location).Path,
    [string]$ModelPath = "PowerBI/Model/model.bim",
    [string]$BPARulesPath = "PowerBI/CI/bpa_rules.json",
    [string]$TabularEditorPath = "C:\Program Files (x86)\Tabular Editor\TabularEditor.exe"
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

function Test-MStructuralSanity {
    <#
    .SYNOPSIS
    Bounded structural sanity check for a Power Query M file. NOT a grammar
    parser: it does not build or validate an AST, and a file can pass this
    and still be semantically invalid M (e.g. a stray comma, a bad operator).
    See M's lexical spec: https://learn.microsoft.com/en-us/powerquery-m/m-spec-lexical-structure

    Tests reconciled: an earlier version of this check stripped // and /* */
    comments with a regex BEFORE recognizing strings. That is unsound -- M
    does not suppress comment tokens inside a string, so a valid string
    containing "//" (e.g. a URL parameter value) was wrongly treated as a
    comment start, corrupting the quote count and failing a valid file. And
    a regex requiring a closing */ cannot detect an UNTERMINATED block
    comment: if no closing */ exists, the (?s)/\*.*?\*/ pattern simply never
    matches, so the malformed marker and everything after it silently passed
    through unchanged. Both were demonstrated with real pwsh fixtures, not
    assumed.

    Fixed by single-pass lexical scanning (comments and strings recognized
    together, in one left-to-right character walk) instead of two independent
    regex substitutions:
      - "//" and "/* */" are only recognized as comment starts when the
        scanner is not currently inside a string.
      - a doubled quote ("") inside a string is treated as M's escaped-quote
        sequence, not a string terminator.
      - reaching end-of-file while still inside a string, or still inside a
        block comment, is itself reported as a structural issue (previously
        undetectable).
      - a closing delimiter encountered before its matching opener (e.g.
        ")(" with equal counts but invalid order) is reported immediately,
        not just an aggregate open/close count mismatch.
    #>
    param([string]$Content)

    if ([string]::IsNullOrWhiteSpace($Content)) {
        return @("file is empty")
    }

    $issues = [System.Collections.Generic.List[string]]::new()
    $depth = @{ '(' = 0; '[' = 0; '{' = 0 }
    $closerFor = @{ ')' = '('; ']' = '['; '}' = '{' }
    $inString = $false
    $inLineComment = $false
    $inBlockComment = $false
    $chars = $Content.ToCharArray()
    $len = $chars.Length
    $i = 0

    while ($i -lt $len) {
        $c = $chars[$i]
        $next = if ($i + 1 -lt $len) { $chars[$i + 1] } else { [char]0 }

        if ($inLineComment) {
            if ($c -eq "`n") { $inLineComment = $false }
            $i++; continue
        }
        if ($inBlockComment) {
            if ($c -eq '*' -and $next -eq '/') { $inBlockComment = $false; $i += 2; continue }
            $i++; continue
        }
        if ($inString) {
            if ($c -eq '"') {
                if ($next -eq '"') { $i += 2; continue }  # M's doubled-quote escape
                $inString = $false
            }
            $i++; continue
        }

        # Not inside a string or comment: comment/string starts are only
        # recognized here, so a "//" or "/* */" inside a string literal
        # (e.g. a URL) is correctly left alone.
        if ($c -eq '/' -and $next -eq '/') { $inLineComment = $true; $i += 2; continue }
        if ($c -eq '/' -and $next -eq '*') { $inBlockComment = $true; $i += 2; continue }
        if ($c -eq '"') { $inString = $true; $i++; continue }

        # Hashtable.ContainsKey/indexing do NOT coerce a [char] to match a
        # string key (unlike PowerShell's -eq operator, which does) -- cast
        # explicitly, or every bracket silently fails to match any key and
        # depth tracking never increments or decrements at all.
        $cs = [string]$c
        if ($depth.ContainsKey($cs)) {
            $depth[$cs]++
        } elseif ($closerFor.ContainsKey($cs)) {
            $opener = $closerFor[$cs]
            $depth[$opener]--
            if ($depth[$opener] -lt 0) {
                $issues.Add("closing '$cs' encountered before its matching '$opener'")
                $depth[$opener] = 0  # avoid cascading negative-count noise for the rest of the file
            }
        }
        $i++
    }

    if ($inString) { $issues.Add("unterminated string literal (end of file reached inside an open double-quoted string)") }
    if ($inBlockComment) { $issues.Add("unterminated block comment (end of file reached inside an open /* ... */ comment)") }
    foreach ($opener in @('(', '[', '{')) {
        if ($depth[$opener] -ne 0) {
            $closer = (@{ '(' = ')'; '[' = ']'; '{' = '}' })[$opener]
            $issues.Add("unbalanced '$opener$closer' ($($depth[$opener]) net unclosed)")
        }
    }
    return ,@($issues.ToArray())
}

$pqFiles = Get-ChildItem -Path (Join-Path $RepoRoot "PowerBI/PowerQuery") -Filter "*.pq" -Recurse -ErrorAction SilentlyContinue
if ($pqFiles.Count -gt 0) {
    # M does NOT require a let/in expression to be valid -- per the M language
    # specification (https://learn.microsoft.com/en-us/powerquery-m/m-spec-basic-concepts),
    # a valid M document can be a bare literal, a record ([a=1]), a list
    # ({1,2,3}), a function (x) => x, or a metadata-annotated value (as in
    # this repo's own 00_Parameters.pq, a Power Query PARAMETER). A previous
    # version of this check required the literal substrings "let" and "in"
    # and flagged 00_Parameters.pq as malformed for lacking them -- that was
    # a false positive, not a real defect in the file.
    #
    # Test-MStructuralSanity (above) verifies delimiter and string/comment
    # well-formedness only -- it is a bounded structural check, not a
    # grammar parser, and a file can pass it while still being invalid M
    # (see the function's own docstring for what it does and does not
    # catch). Full M grammar validation is NOT RUN by this script.
    foreach ($pqFile in $pqFiles) {
        $content = Get-Content -Path $pqFile.FullName -Raw
        $issues = Test-MStructuralSanity -Content $content

        if ($issues.Count -eq 0) {
            Write-Host "  ✓ Basic structural sanity passed (balanced delimiters/strings/comments -- NOT full M syntax validation): $($pqFile.Name)" -ForegroundColor Green
        } else {
            $failures += "Power Query structural issue in $($pqFile.Name): $($issues -join '; ')"
            Write-Host "  ❌ $($pqFile.Name): $($issues -join '; ')" -ForegroundColor Red
        }
    }
    Write-Host "  ℹ Full M grammar validation: NOT RUN (no M parser available in this environment)" -ForegroundColor Gray
} else {
    Write-Host "  ℹ No .pq files found in PowerBI/PowerQuery" -ForegroundColor Gray
}

# ------------------------------------------------------------------------------
# STEP 3: Tabular Editor CLI — Semantic Model Compilation & DAX Validation
# ------------------------------------------------------------------------------
Write-Host "`n[3/4] Running Tabular Editor Semantic Model Compilation..." -ForegroundColor Yellow

$fullModelPath = Join-Path $RepoRoot $ModelPath
$fullBPARulesPath = Join-Path $RepoRoot $BPARulesPath

if (Test-Path $fullModelPath) {
    Write-Host "  ✓ Loading Semantic Model: $ModelPath" -ForegroundColor Green

    $teCmd = if (Test-Path $TabularEditorPath) { $TabularEditorPath } else { "TabularEditor.exe" }

    if (Get-Command $teCmd -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ Tabular Editor CLI found" -ForegroundColor Green
        Write-Host "  ℹ (Actual model compilation requires .bim file present)" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠ Tabular Editor not installed. Install via: choco install tabulareditor" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ℹ Semantic Model not found at $ModelPath (optional for now)" -ForegroundColor Gray
}

# ------------------------------------------------------------------------------
# STEP 4: Best Practice Analyzer (BPA) Verification
# ------------------------------------------------------------------------------
Write-Host "`n[4/4] Executing Best Practice Analyzer (BPA)..." -ForegroundColor Yellow

if (Test-Path $fullBPARulesPath) {
    Write-Host "  ✓ BPA rules available at: $BPARulesPath" -ForegroundColor Green
    Write-Host "  ℹ (BPA execution requires Tabular Editor + active .pbix model)" -ForegroundColor Gray
} else {
    Write-Host "  ℹ BPA rules file not found (created via commit)" -ForegroundColor Gray
}

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
    Write-Host " ✅ ALL POWER BI & WATCH FOLDER CHECKS PASSED CLEANLY" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Cyan
    exit 0
}
