#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs Power BI Desktop on a Windows machine, for mt-dashboard's
    PowerBI/ build-kit validation (see PowerBI/docs/RefreshGuide.md and
    PowerBI/docs/DEPLOYMENT_RUNBOOK.md's "Prerequisites" section).

.DESCRIPTION
    Template script only -- not run or validated from this session (no
    Windows machine available in that environment). Test on one VM before
    any wider rollout via Intune/Group Policy/SCCM.

    Tries winget first (the Microsoft-recommended path on Windows 10 2004+
    / Windows 11), falls back to Chocolatey if winget isn't available.
    Neither package manager's presence or the eventual install has been
    verified end-to-end -- confirm both work on your actual target image
    before relying on this in an unattended rollout.

.NOTES
    Run as Administrator. Requires internet access to the Microsoft Store
    / winget repo (or the Chocolatey community repo as a fallback).
#>

$ErrorActionPreference = "Stop"

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Output "=== Power BI Desktop silent install ==="

# ---- Already installed? Skip if so. ----
$existing = Get-AppxPackage -Name "*PowerBI*" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "Power BI Desktop already installed (version $($existing.Version)). Nothing to do."
    exit 0
}

# ---- Path 1: winget ----
if (Test-Command "winget") {
    Write-Output "winget found. Installing Power BI Desktop..."
    # Verify the exact package ID on your machine first:
    #   winget search "Power BI Desktop"
    # Package IDs seen in the wild: Microsoft.PowerBI (Store) or
    # Microsoft.PowerBIDesktop (win32, in some winget repo revisions) --
    # confirm which one `winget search` returns before relying on this
    # unattended; the wrong ID fails fast and loud rather than silently.
    winget install --id Microsoft.PowerBI -e --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Output "winget install failed (exit $LASTEXITCODE). Falling back to Chocolatey if available."
    } else {
        Write-Output "Power BI Desktop installed via winget."
        exit 0
    }
}

# ---- Path 2: Chocolatey fallback ----
if (Test-Command "choco") {
    Write-Output "Installing Power BI Desktop via Chocolatey..."
    choco install microsoft-powerbi -y
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Chocolatey install failed (exit $LASTEXITCODE)."
        exit 1
    }
    Write-Output "Power BI Desktop installed via Chocolatey."
    exit 0
}

Write-Output "Neither winget nor choco is available on this machine."
Write-Output "Install winget (App Installer from the Microsoft Store, or the"
Write-Output "standalone MSIX bundle from https://github.com/microsoft/winget-cli/releases),"
Write-Output "or install Chocolatey (https://chocolatey.org/install), then re-run this script."
exit 1
