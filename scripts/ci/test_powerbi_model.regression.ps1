# ==============================================================================
# test_powerbi_model.regression.ps1
#
# Regression fixtures for scripts/ci/test_powerbi_model.ps1's Power Query
# structural sanity check (Test-MStructuralSanity). Each case here reproduces
# a specific defect found and fixed during development -- run this after any
# change to the PQ-checking logic in test_powerbi_model.ps1 to confirm none
# of them regress.
#
# Usage:
#   pwsh -File scripts/ci/test_powerbi_model.regression.ps1
# Exits 0 if every fixture's actual exit code matches its expected one,
# exits 1 and prints a diff of expected vs actual otherwise.
# ==============================================================================
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$scriptUnderTest = Join-Path $PSScriptRoot "test_powerbi_model.ps1"
$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("pq_regression_" + [System.Guid]::NewGuid().ToString("N"))

function New-Fixture {
    param([string]$Name, [string]$FileName, [string]$Content)
    $dir = Join-Path $workDir "$Name/PowerBI/PowerQuery"
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Set-Content -Path (Join-Path $dir $FileName) -Value $Content -NoNewline
    return (Join-Path $workDir $Name)
}

$cases = @()

# 1. The real 00_Parameters.pq shape: a parameter, no let/in.
$cases += @{
    Name = "real parameter file (no let/in)"
    Path = New-Fixture "case01" "00_Parameters.pq" @'
"C:\MT-Dashboard" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
'@
    ExpectedExit = 0
}

# 2. Ordinary let/in query.
$cases += @{
    Name = "let/in query"
    Path = New-Fixture "case02" "Query.pq" @'
let
    Source = Table.FromRecords({[a=1,b=2]})
in
    Source
'@
    ExpectedExit = 0
}

# 3-5. Valid M shapes that never contain let/in -- the old parameter-only
# exemption would still have wrongly rejected these.
$cases += @{
    Name = "record-only expression (no let/in)"
    Path = New-Fixture "case03" "Config.pq" @'
[
    Environment = "Production",
    RootPath = "C:\Data",
    RetryCount = 3
]
'@
    ExpectedExit = 0
}
$cases += @{
    Name = "function-only expression (no let/in)"
    Path = New-Fixture "case04" "fnAddTax.pq" @'
(amount as number, rate as number) as number =>
    amount * (1 + rate)
'@
    ExpectedExit = 0
}
$cases += @{
    Name = "list-only expression (no let/in)"
    Path = New-Fixture "case05" "Zones.pq" @'
{
    "North",
    "South",
    "East",
    "West"
}
'@
    ExpectedExit = 0
}

# 6. Genuinely broken: missing closing bracket.
$cases += @{
    Name = "genuinely broken (unclosed record)"
    Path = New-Fixture "case06" "Broken.pq" @'
[
    Environment = "Production",
    RootPath = "C:\Data"
'@
    ExpectedExit = 1
}

# 7. "let"/"in" appear only in a comment; file is still structurally broken.
$cases += @{
    Name = 'let/in in a misleading comment, still broken'
    Path = New-Fixture "case07" "Misleading.pq" @'
// TODO: rewrite this as a let ... in expression later
[
    Environment = "Production"
'@
    ExpectedExit = 1
}

# 8. "let"/"in" appear only inside a string literal; file is still broken.
$cases += @{
    Name = 'let/in inside a string literal, still broken'
    Path = New-Fixture "case08" "StringTrap.pq" @'
[
    Message = "let me know when you check in",
    Broken = Text.From(123
]
'@
    ExpectedExit = 1
}

# 9. Empty file.
$cases += @{
    Name = "empty file"
    Path = New-Fixture "case09" "Empty.pq" ""
    ExpectedExit = 1
}

# 10. "//" inside a string literal (e.g. a URL) must NOT be treated as a
# comment start -- a naive regex-strip-then-count approach gets this wrong.
$cases += @{
    Name = '"//" inside a string literal (URL) is not a comment'
    Path = New-Fixture "case10" "UrlParam.pq" @'
"https://example.com/data" meta [IsParameterQuery=true, Type="Text"]
'@
    ExpectedExit = 0
}

# 11. "/* */"-looking text inside a string, file broken for an unrelated
# reason (unclosed paren) -- must fail for the real reason, not be
# corrupted by comment-stripping inside the string.
$cases += @{
    Name = '"/* */" text inside a string, broken elsewhere'
    Path = New-Fixture "case11" "BlockInString.pq" @'
[
    Note = "see /* details */ in the wiki",
    Broken = Text.From(123
]
'@
    ExpectedExit = 1
}

# 12. Quoted identifier syntax #"Column Name" must not corrupt quote parity.
$cases += @{
    Name = 'quoted identifier #"..."'
    Path = New-Fixture "case12" "QuotedIdent.pq" @'
let
    Source = Table.FromRecords({[#"Column One" = 1, #"Column (Two)" = 2]}),
    Renamed = Table.RenameColumns(Source, {{"#Column One", "A"}})
in
    Renamed
'@
    ExpectedExit = 0
}

# 13. Unterminated string literal.
$cases += @{
    Name = "unterminated string literal"
    Path = New-Fixture "case13" "Unterminated.pq" @'
[
    Note = "this string never closes
]
'@
    ExpectedExit = 1
}

# 14. Unterminated block comment -- a regex requiring a closing */ cannot
# detect this at all (it simply never matches, so nothing gets stripped).
$cases += @{
    Name = "unterminated block comment"
    Path = New-Fixture "case14" "UnterminatedComment.pq" @'
[
    A = 1,
/* this comment never closes
    B = 2
]
'@
    ExpectedExit = 1
}

# 15. Mismatched delimiter ORDER with EQUAL open/close counts -- an
# aggregate count comparison alone cannot catch this.
$cases += @{
    Name = "mismatched delimiter order, equal counts"
    Path = New-Fixture "case15" "MismatchedOrder.pq" @'
[
    A = )Text.From(1
]
'@
    ExpectedExit = 1
}

# 16. Balanced but semantically invalid M (stray commas) -- expected to
# PASS this structural check; full grammar validation is explicitly out
# of scope and disclosed as such.
$cases += @{
    Name = "balanced but semantically invalid (out of scope, should pass)"
    Path = New-Fixture "case16" "BalancedInvalid.pq" @'
[
    A = 1,,
    B = ,
]
'@
    ExpectedExit = 0
}

# 17. A real path containing spaces.
$cases += @{
    Name = "path containing spaces"
    Path = New-Fixture "case17 with spaces" "00_Parameters.pq" @'
"C:\MT-Dashboard" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
'@
    ExpectedExit = 0
}

$failed = @()
foreach ($case in $cases) {
    $actualExit = 0
    & $scriptUnderTest -RepoRoot $case.Path *> $null
    $actualExit = $LASTEXITCODE
    $status = if ($actualExit -eq $case.ExpectedExit) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1} (expected exit {2}, got {3})" -f $status, $case.Name, $case.ExpectedExit, $actualExit)
    if ($status -eq "FAIL") { $failed += $case.Name }
}

Remove-Item -Path $workDir -Recurse -Force -ErrorAction SilentlyContinue

if ($failed.Count -gt 0) {
    Write-Host "`n$($failed.Count) of $($cases.Count) regression fixture(s) FAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "`nAll $($cases.Count) regression fixtures passed." -ForegroundColor Green
exit 0
