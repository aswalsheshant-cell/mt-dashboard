<#
.SYNOPSIS
    Automated Pre-Flight Checklist Verification Script for PBIP Assembly.
.DESCRIPTION
    Validates the 9 pre-deployment requirements:
      1. Git installation
      2. Python version (>= 3.10)
      3. pip functionality
      4. Syntax validation of build_dashboard_data.py
      5. Python virtual environment activation state
      6. Required Python package installations
      7. Critical library imports (openpyxl, lxml, pptx)
      8. Power BI Desktop installation & launch check
      9. Power BI Service endpoint / Fabric connectivity check
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Verify-Preflight.ps1
#>

[CmdletBinding()]
param (
    [string]$RepoRoot = (Get-Location).Path,
    [string]$VenvPath = ".\venv"
)

$Host.UI.RawUI.WindowTitle = "Modern Trade Pre-Flight Environment Validation"
Clear-Host

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   PRE-FLIGHT ENVIRONMENT & TOOLCHAIN VERIFICATION          " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Working Directory: $RepoRoot`n"

$results = [System.Collections.Generic.List[PSCustomObject]]::new()

function Record-Check {
    param (
        [int]$ItemNumber,
        [string]$Description,
        [bool]$Passed,
        [string]$Details
    )

    $statusString = if ($Passed) { "[PASS]" } else { "[FAIL]" }
    $color = if ($Passed) { "Green" } else { "Red" }

    Write-Host ("{0,-7} Check {1}: {2}" -f $statusString, $ItemNumber, $Description) -ForegroundColor $color
    if (-not [string]::IsNullOrWhiteSpace($Details)) {
        Write-Host ("        Details: {0}" -f $Details) -ForegroundColor Gray
    }

    $results.Add([PSCustomObject]@{
        ItemNumber  = $ItemNumber
        Description = $Description
        Status      = if ($Passed) { "PASS" } else { "FAIL" }
        Details     = $Details
    })
}

# --- Item 1: Git Installation ---
try {
    $gitVer = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Record-Check 1 "Git Installed" $true $gitVer.Trim()
    } else {
        Record-Check 1 "Git Installed" $false "Git command returned non-zero exit code."
    }
} catch {
    Record-Check 1 "Git Installed" $false "Git executable not found in PATH."
}

# --- Item 2: Python Version (>= 3.10) ---
$pythonCmd = $null
if (Test-Path "$VenvPath\Scripts\python.exe") {
    $pythonCmd = "$VenvPath\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
}

if ($pythonCmd) {
    try {
        $pyVerRaw = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1
        $versionParts = $pyVerRaw.Trim().Split('.')
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]

        if ($major -eq 3 -and $minor -ge 10) {
            Record-Check 2 "Python Version (>= 3.10)" $true "Found Python $pyVerRaw ($pythonCmd)"
        } else {
            Record-Check 2 "Python Version (>= 3.10)" $false "Detected version $pyVerRaw does not meet >= 3.10 requirement."
        }
    } catch {
        Record-Check 2 "Python Version (>= 3.10)" $false "Failed to execute Python version check."
    }
} else {
    Record-Check 2 "Python Version (>= 3.10)" $false "No Python executable found."
}

# --- Item 3: pip Functionality ---
if ($pythonCmd) {
    try {
        $pipVer = & $pythonCmd -m pip --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Record-Check 3 "Pip Functional" $true $pipVer.Trim()
        } else {
            Record-Check 3 "Pip Functional" $false "Pip command returned non-zero exit code."
        }
    } catch {
        Record-Check 3 "Pip Functional" $false "Error invoking pip."
    }
} else {
    Record-Check 3 "Pip Functional" $false "Skipped: Python unavailable."
}

# --- Item 4: Syntax Check on build_dashboard_data.py ---
$scriptPath = Join-Path $RepoRoot "scripts\build_dashboard_data.py"
if (Test-Path $scriptPath) {
    if ($pythonCmd) {
        $compileOut = & $pythonCmd -m py_compile $scriptPath 2>&1
        if ($LASTEXITCODE -eq 0) {
            Record-Check 4 "Dashboard Script Syntax" $true "scripts/build_dashboard_data.py compiled successfully."
        } else {
            Record-Check 4 "Dashboard Script Syntax" $false "Compilation errors: $compileOut"
        }
    } else {
        Record-Check 4 "Dashboard Script Syntax" $false "Skipped: Python unavailable."
    }
} else {
    Record-Check 4 "Dashboard Script Syntax" $false "Target file not found: $scriptPath"
}

# --- Item 5: Virtual Environment Activation State / Presence ---
$venvActivate = Join-Path $RepoRoot "$VenvPath\Scripts\activate.ps1"
if (Test-Path $venvActivate) {
    $inVenv = ($env:VIRTUAL_ENV -ne $null) -or ($pythonCmd -like "*venv*")
    if ($inVenv) {
        Record-Check 5 "Virtual Environment Ready" $true "Active venv detected at $VenvPath"
    } else {
        Record-Check 5 "Virtual Environment Ready" $true "Found at $VenvPath (Execute .\venv\Scripts\Activate.ps1 to activate in current shell)"
    }
} else {
    Record-Check 5 "Virtual Environment Ready" $false "Virtual environment not detected at $VenvPath. Run: python -m venv venv"
}

# --- Item 6: Python Dependencies Installed (requirements.txt) ---
$reqFile = Join-Path $RepoRoot "requirements.txt"
if ((Test-Path $reqFile) -and $pythonCmd) {
    try {
        $missingList = & $pythonCmd -c "
import pkg_resources, sys
reqs = [str(r.req) for r in pkg_resources.parse_requirements(open(r'$reqFile')) if r.req]
missing = []
for r in reqs:
    try:
        pkg_resources.require(r)
    except Exception:
        missing.append(r)
if missing:
    print(','.join(missing))
    sys.exit(1)
" 2>&1

        if ($LASTEXITCODE -eq 0) {
            Record-Check 6 "Requirements Installed" $true "All packages in requirements.txt are installed."
        } else {
            Record-Check 6 "Requirements Installed" $false "Missing or unsatisfied dependencies: $missingList"
        }
    } catch {
        Record-Check 6 "Requirements Installed" $false "Dependency check failed to run."
    }
} else {
    Record-Check 6 "Requirements Installed" $false "requirements.txt not found or Python runtime unavailable."
}

# --- Item 7: Key Library Imports ---
if ($pythonCmd) {
    $importTest = & $pythonCmd -c "import openpyxl, lxml, pptx; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0 -and $importTest -match "OK") {
        Record-Check 7 "Core Libraries Import" $true "openpyxl, lxml, and python-pptx imported successfully."
    } else {
        Record-Check 7 "Core Libraries Import" $false "Import failed: $importTest"
    }
} else {
    Record-Check 7 "Core Libraries Import" $false "Skipped: Python unavailable."
}

# --- Item 8: Power BI Desktop Installed ---
$pbiRegistryPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Microsoft Power BI Desktop",
    "HKCU:\SOFTWARE\Microsoft\Microsoft Power BI Desktop"
)
$pbiStoreApp = Get-AppxPackage -Name "*PowerBIDesktop*" -ErrorAction SilentlyContinue
$pbiExe = Get-Command "PBIDesktop.exe" -ErrorAction SilentlyContinue
$foundPBI = $false
$pbiLocation = ""

if ($pbiStoreApp) {
    $foundPBI = $true
    $pbiLocation = "Microsoft Store App ($($pbiStoreApp.Version))"
} elseif ($pbiExe) {
    $foundPBI = $true
    $pbiLocation = $pbiExe.Source
} else {
    foreach ($path in $pbiRegistryPaths) {
        if (Test-Path $path) {
            $foundPBI = $true
            $pbiLocation = "Registry Entry: $path"
            break
        }
    }
}

if ($foundPBI) {
    Record-Check 8 "Power BI Desktop Installed" $true $pbiLocation
} else {
    Record-Check 8 "Power BI Desktop Installed" $false "PBIDesktop.exe not found via Store, PATH, or Registry."
}

# --- Item 9: Power BI Service Connectivity ---
try {
    $tcpCheck = Test-NetConnection -ComputerName "api.powerbi.com" -Port 443 -WarningAction SilentlyContinue
    if ($tcpCheck.TcpTestSucceeded) {
        Record-Check 9 "Power BI Service Reachable" $true "Port 443 open to api.powerbi.com"
    } else {
        Record-Check 9 "Power BI Service Reachable" $false "Network route or firewall blocking api.powerbi.com:443"
    }
} catch {
    Record-Check 9 "Power BI Service Reachable" $false "Unable to test network connectivity: $_"
}

# =====================================================================
# Summary
# =====================================================================

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   SUMMARY                                                 " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$passedCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failedCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$totalCount  = $results.Count

Write-Host "Passed: $passedCount / $totalCount" -ForegroundColor $(if ($passedCount -eq $totalCount) { "Green" } else { "Yellow" })
Write-Host "Failed: $failedCount / $totalCount" -ForegroundColor $(if ($failedCount -eq 0) { "Green" } else { "Red" })

if ($failedCount -gt 0) {
    Write-Host "`nAction Required: Resolve the failed checks before kickoff." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "`nAll pre-flight checks passed! Environment is ready for PBIP assembly." -ForegroundColor Green
    exit 0
}
