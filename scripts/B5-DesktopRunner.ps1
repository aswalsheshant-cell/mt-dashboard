<#
.SYNOPSIS
    B5 Desktop runner: runs the governed CM2 / rolling-average DAX cases on the model that is
    OPEN in Power BI Desktop and hands the raw results to scripts/b5_evidence.py.

.DESCRIPTION
    *** UNTESTED against a real engine. ***  It was written without Windows or a DAX engine
    available (CI has neither). The first run on your machine is its first test: read the
    console output, and if anything looks off, stop and send me the output.

    What it does
      1. asks scripts/b5_evidence.py for the governed EVALUATE blocks (--emit-queries), so the
         queries are exactly the ones in tests/powerbi/*_cases.dax, not a copy;
      2. finds the local Analysis Services port of the open Desktop model
         (AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt, fallback: the msmdsrv process);
      3. runs each block on its own through ADOMD.NET and records the result tables;
      4. writes results.json (outside the repo) with the metadata the evidence file needs;
      5. calls scripts/b5_evidence.py, which applies the run sheet's PASS rules.

    What it does not do
      * It does not write evidence itself and it does not decide PASS or FAIL: scripts/b5_evidence.py does.
      * It cannot run the FY parser (Power Query M is not reachable through Analysis Services):
        paste tests/powerbi/pq39_fy_parser_cases.pq in Desktop, then pass -FyParserFailures N
        and -AttestedBy "<your name>". Without them that row stays NOT_RUN.
      * It cannot take screenshots. Attach one per step, as the run sheet requires.

    Before you run it
      * git checkout the frozen main SHA, clean working tree.
      * Open the model in Power BI Desktop and press Home > Refresh. Wait for it to finish.
      * Python 3 on PATH (python or py -3) with the repo requirements (pandas is not needed).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\B5-DesktopRunner.ps1 -RunBy "MT Channel Analyst Lead" -Refreshed

.EXAMPLE
    # after pasting the FY parser query in Desktop and seeing Failures = 0 rows
    powershell -ExecutionPolicy Bypass -File .\scripts\B5-DesktopRunner.ps1 -Refreshed -FyParserFailures 0 -AttestedBy "Your Name" -ExpectSha b6f2776
#>
[CmdletBinding()]
param (
    [string]$RepoRoot = '',
    [int]$Port = 0,
    [string]$ModelFile = '',
    [string]$DesktopVersion = '',
    [string]$ResultsPath = '',
    [string]$RunBy = '',
    [switch]$Refreshed,
    [int]$FyParserFailures = -1,
    [string]$AttestedBy = '',
    [string]$ExpectSha = '',
    [switch]$AllowDirty,
    [switch]$SkipEvidence
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
$EvidenceScript = Join-Path $RepoRoot 'scripts\b5_evidence.py'
if (-not (Test-Path $EvidenceScript)) { throw "scripts\b5_evidence.py not found under $RepoRoot" }

function Get-PythonCommand {
    foreach ($c in @('python', 'py')) {
        if (Get-Command $c -ErrorAction SilentlyContinue) {
            if ($c -eq 'py') { return @('py', '-3') }
            return @($c)
        }
    }
    throw 'Python 3 was not found on PATH (tried python, py).'
}

function Invoke-Python {
    param ([string[]]$PyArgs)
    $py = Get-PythonCommand
    $exe = $py[0]
    $pre = @()
    if ($py.Count -gt 1) { $pre = $py[1..($py.Count - 1)] }
    & $exe @pre @PyArgs
    return $LASTEXITCODE
}

function Get-AnalysisServicesPort {
    if ($Port -gt 0) { return $Port }
    $base = Join-Path $env:LOCALAPPDATA 'Microsoft\Power BI Desktop\AnalysisServicesWorkspaces'
    $files = @()
    if (Test-Path $base) {
        $files = @(Get-ChildItem -Path $base -Recurse -Filter 'msmdsrv.port.txt' -ErrorAction SilentlyContinue |
                   Sort-Object LastWriteTime -Descending)
    }
    if ($files.Count -ge 1) {
        if ($files.Count -gt 1) {
            Write-Warning ("{0} Desktop workspaces found; using the newest. If you have several models open, " +
                           "close the others or pass -Port." -f $files.Count)
        }
        $txt = (Get-Content -Path $files[0].FullName -Encoding Unicode -Raw).Trim()
        $p = 0
        if ([int]::TryParse($txt, [ref]$p) -and $p -gt 0) { return $p }
    }
    $procs = @(Get-Process -Name msmdsrv -ErrorAction SilentlyContinue)
    if ($procs.Count -eq 1) {
        $conn = Get-NetTCPConnection -OwningProcess $procs[0].Id -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.LocalAddress -in @('127.0.0.1', '::1') } | Select-Object -First 1
        if ($conn) { return [int]$conn.LocalPort }
    }
    throw 'Could not find the open model''s Analysis Services port. Open the model in Power BI Desktop, or pass -Port.'
}

function Import-AdomdClient {
    try { Add-Type -AssemblyName 'Microsoft.AnalysisServices.AdomdClient' -ErrorAction Stop; return } catch { }
    $candidates = @(
        "$env:ProgramFiles\Microsoft Power BI Desktop\bin\Microsoft.AnalysisServices.AdomdClient.dll",
        "${env:ProgramFiles(x86)}\Microsoft.NET\ADOMD.NET\160\Microsoft.AnalysisServices.AdomdClient.dll",
        "$env:ProgramFiles\Microsoft.NET\ADOMD.NET\160\Microsoft.AnalysisServices.AdomdClient.dll",
        "${env:ProgramFiles(x86)}\Microsoft.NET\ADOMD.NET\150\Microsoft.AnalysisServices.AdomdClient.dll",
        "${env:ProgramFiles(x86)}\Microsoft.NET\ADOMD.NET\140\Microsoft.AnalysisServices.AdomdClient.dll"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { Add-Type -Path $c; return }
    }
    $found = Get-ChildItem -Path $env:ProgramFiles, ${env:ProgramFiles(x86)} -Recurse -Filter 'Microsoft.AnalysisServices.AdomdClient.dll' `
             -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { Add-Type -Path $found.FullName; return }
    throw 'Microsoft.AnalysisServices.AdomdClient.dll not found. Install ADOMD.NET (or DAX Studio / SSMS) and re-run.'
}

function ConvertTo-JsonValue {
    param ($v)
    if ($null -eq $v -or $v -is [System.DBNull]) { return $null }
    if ($v -is [datetime]) { return $v.ToString('yyyy-MM-dd') }
    if ($v -is [double] -or $v -is [single] -or $v -is [decimal] -or $v -is [int] -or $v -is [long] -or $v -is [int16]) { return $v }
    if ($v -is [bool]) { return $v }
    return [string]$v
}

function Invoke-DaxTable {
    param ($Connection, [string]$Text)
    $cmd = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdCommand($Text, $Connection)
    $cmd.CommandTimeout = 300
    $rdr = $cmd.ExecuteReader()
    try {
        $cols = New-Object System.Collections.ArrayList
        for ($i = 0; $i -lt $rdr.FieldCount; $i++) { [void]$cols.Add($rdr.GetName($i)) }
        $rows = New-Object System.Collections.ArrayList
        while ($rdr.Read()) {
            $r = New-Object System.Collections.ArrayList
            for ($i = 0; $i -lt $rdr.FieldCount; $i++) { [void]$r.Add((ConvertTo-JsonValue $rdr.GetValue($i))) }
            [void]$rows.Add($r)
        }
        return [ordered]@{ columns = $cols; rows = $rows }
    }
    finally { $rdr.Close() }
}

# ---------------------------------------------------------------------------------------
Write-Host '=== B5 Desktop runner (UNTESTED against a real engine: your first run is its first test) ===' -ForegroundColor Yellow

# 1. governed queries (single source of truth: scripts/b5_evidence.py)
$tmp = Join-Path $env:TEMP ('b5_run_' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $tmp | Out-Null
$queriesPath = Join-Path $tmp 'queries.json'
$rc = Invoke-Python @($EvidenceScript, '--emit-queries', $queriesPath)
if ($rc -ne 0) { throw "b5_evidence.py --emit-queries failed (exit $rc)" }
$queryDoc = Get-Content -Path $queriesPath -Raw -Encoding UTF8 | ConvertFrom-Json
$queries = [ordered]@{}
foreach ($p in $queryDoc.queries.PSObject.Properties) { $queries[$p.Name] = [string]$p.Value }
Write-Host ("Governed queries: {0}" -f $queries.Count)

# 2. repo state
$gitSha = (& git -C $RepoRoot rev-parse --short HEAD).Trim()
$dirtyOut = & git -C $RepoRoot status --porcelain --untracked-files=no
$gitDirty = [bool]$dirtyOut
Write-Host ("Repo SHA: {0}  working tree dirty: {1}" -f $gitSha, $gitDirty)
if ($ExpectSha -and -not ($gitSha.StartsWith($ExpectSha) -or $ExpectSha.StartsWith($gitSha))) {
    throw "Repo SHA $gitSha is not the expected frozen SHA $ExpectSha. Check out the frozen SHA first."
}

# 3. connect to the open model
Import-AdomdClient
$asPort = Get-AnalysisServicesPort
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$asPort")
$conn.Open()
$serverVersion = [string]$conn.ServerVersion
Write-Host ("Connected: localhost:{0}  server version {1}" -f $asPort, $serverVersion)

$database = ''
try {
    $cat = Invoke-DaxTable $conn 'SELECT [CATALOG_NAME] FROM $SYSTEM.DBSCHEMA_CATALOGS'
    if ($cat.rows.Count -gt 0) { $database = [string]$cat.rows[0][0] }
} catch { Write-Warning "Could not read the catalog name: $_" }

$measureCount = 0
try {
    $m = Invoke-DaxTable $conn 'SELECT [ID] FROM $SYSTEM.TMSCHEMA_MEASURES'
    $measureCount = $m.rows.Count
} catch { Write-Warning "Could not count measures through TMSCHEMA_MEASURES: $_" }
Write-Host ("Model: {0}  measures: {1}" -f $database, $measureCount)

if (-not $DesktopVersion) {
    try {
        $pbi = Get-Process -Name PBIDesktop -ErrorAction Stop | Select-Object -First 1
        $DesktopVersion = $pbi.MainModule.FileVersionInfo.ProductVersion
        if (-not $ModelFile -and $pbi.MainWindowTitle) { $ModelFile = ($pbi.MainWindowTitle -replace '\s+-\s+Power BI Desktop.*$', '') }
    } catch { Write-Warning "Could not read the Desktop version automatically; pass -DesktopVersion (Help > About)." }
}
if (-not $ModelFile) { Write-Warning 'Model file name unknown; pass -ModelFile.' }

# 4. run every governed block on its own
$cases = [ordered]@{}
$errors = [ordered]@{}
foreach ($key in $queries.Keys) {
    try {
        $t = Invoke-DaxTable $conn $queries[$key]
        $cases[$key] = $t
        Write-Host ("  {0,-14} {1} row(s)" -f $key, $t.rows.Count) -ForegroundColor Green
    } catch {
        $errors[$key] = [string]$_.Exception.Message
        Write-Host ("  {0,-14} ERROR: {1}" -f $key, $_.Exception.Message) -ForegroundColor Red
    }
}
$conn.Close()

# 5. results.json (outside the repo: it holds business numbers; keep it with the screenshots)
if (-not $ResultsPath) { $ResultsPath = Join-Path $tmp 'results.json' }
$doc = [ordered]@{
    meta    = [ordered]@{
        source          = 'live_analysis_services'
        port            = $asPort
        database        = $database
        server_version  = $serverVersion
        measure_count   = $measureCount
        git_sha         = $gitSha
        git_dirty       = $gitDirty
        desktop_version = $DesktopVersion
        model_file      = $ModelFile
        utc             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    queries = $queries
    cases   = $cases
    errors  = $errors
}
$json = ConvertTo-Json -InputObject $doc -Depth 12
[System.IO.File]::WriteAllText($ResultsPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("Raw results written to {0}" -f $ResultsPath)
if ($errors.Count -gt 0) { Write-Warning ("{0} query(ies) failed; their rows will read NOT_RUN." -f $errors.Count) }

if ($SkipEvidence) { Write-Host 'Skipping evidence generation (-SkipEvidence).'; return }

# 6. hand over to the Python side (it applies the PASS rules and writes the evidence file)
$pyArgs = @($EvidenceScript, '--results', $ResultsPath)
if ($RunBy) { $pyArgs += @('--run-by', $RunBy) }
if ($Refreshed) { $pyArgs += '--refreshed' }
if ($FyParserFailures -ge 0) { $pyArgs += @('--fy-parser-failures', "$FyParserFailures", '--attested-by', $AttestedBy) }
if ($ExpectSha) { $pyArgs += @('--expect-sha', $ExpectSha) }
if ($AllowDirty) { $pyArgs += '--allow-dirty' }
$rc = Invoke-Python $pyArgs

Write-Host ''
if ($FyParserFailures -lt 0) {
    Write-Host 'FY parser (row 1) was not entered: paste tests\powerbi\pq39_fy_parser_cases.pq in Desktop, then re-run with -FyParserFailures N -AttestedBy "<name>".' -ForegroundColor Yellow
}
Write-Host 'Next: attach one screenshot per step to the B5 PR, commit the generated evidence file, and keep results.json with the screenshots.'
exit $rc
