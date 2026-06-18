#Requires -Version 5.1
<#
.SYNOPSIS
    Install gitwise on Windows via uv tool install.

.DESCRIPTION
    This installer:
    1. Installs uv if not present (via https://astral.sh/uv/install.ps1).
    2. Runs `uv tool install --upgrade gitwise-cli` (isolated venv, no PyPI pollution).
    3. Prints PATH guidance if `gitwise` is not yet on PATH.

    Supported: Windows 10+ / Windows Server 2016+ with PowerShell 5.1+.
    For macOS/Linux, use install.sh instead.

.PARAMETER Version
    Pin a specific version (default: latest from PyPI). Format: X.Y.Z.

.PARAMETER DryRun
    Print actions without executing them.

.EXAMPLE
    # Remote one-liner (run from PowerShell):
    #   irm https://raw.githubusercontent.com/drzioner/gitwise/main/install.ps1 | iex
#
    # Local invocation with version pin:
    powershell -ExecutionPolicy ByPass -File .\install.ps1 -Version 0.26.1

.EXAMPLE
    # Dry-run inspection:
    powershell -ExecutionPolicy ByPass -File .\install.ps1 -DryRun

.LINK
    https://github.com/drzioner/gitwise
#>

[CmdletBinding()]
param(
    [string]$Version = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-UvInstaller {
    # Download and run the official uv standalone installer for Windows.
    # Verified: https://docs.astral.sh/uv/getting-started/installation/
    & powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

function Refresh-SessionPath {
    # The uv installer writes to the User PATH env var. Refresh the current
    # session so `Get-Command uv` can find the newly installed binary.
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $env:Path = "$userPath;$machinePath"
}

# --- Step 1: ensure uv is available ---
$needUvInstall = $false
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvVersion = & $uvCmd.Source --version 2>$null
    Write-Host "uv: present ($uvVersion)"
} else {
    $needUvInstall = $true
    Write-Host "uv: not found"
}

# --- Step 2: determine install spec ---
if ($Version) {
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        Write-Error "Invalid -Version '$Version'. Expected X.Y.Z."
        exit 2
    }
    $packageSpec = "gitwise-cli==$Version"
    Write-Host "target version: $Version"
} else {
    $packageSpec = "gitwise-cli"
    Write-Host "target version: latest"
}

if ($DryRun) {
    Write-Host ""
    Write-Host "[dry-run] plan:"
    if ($needUvInstall) {
        Write-Host "  - irm https://astral.sh/uv/install.ps1 | iex"
    }
    if ($Version) {
        Write-Host "  - uv tool install $packageSpec"
    } else {
        Write-Host "  - uv tool install --upgrade $packageSpec"
    }
    Write-Host "  - print PATH guidance if gitwise not on PATH"
    return
}

# --- Step 3: install uv if needed ---
if ($needUvInstall) {
    Write-Host ""
    Write-Host "Installing uv (https://astral.sh/uv)..."
    Invoke-UvInstaller
    Refresh-SessionPath

    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Write-Error @"
uv installer finished but 'uv' is not on PATH.
Open a new PowerShell window and re-run, or add manually:
  [Environment]::SetEnvironmentVariable('Path', "`$env:USERPROFILE\.local\bin;" + [Environment]::GetEnvironmentVariable('Path', 'User'), 'User')
"@
        exit 1
    }
    Write-Host "uv installed: $($uvCmd.Source)"
}

# --- Step 4: install gitwise via uv tool install ---
Write-Host ""
if ($Version) {
    Write-Host "Installing gitwise $Version..."
    & uv tool install $packageSpec
} else {
    Write-Host "Installing/upgrading gitwise..."
    & uv tool install --upgrade $packageSpec
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "uv tool install failed with exit code $LASTEXITCODE."
    exit 1
}

# --- Step 5: verify and print PATH guidance ---
$uvBinDir = Join-Path $env:USERPROFILE ".local\bin"
$gitwiseCmd = Get-Command gitwise -ErrorAction SilentlyContinue
if ($gitwiseCmd) {
    $installedVersion = & gitwise --version 2>$null
    if (-not $installedVersion) { $installedVersion = "unknown" }
    Write-Host ""
    Write-Host "$installedVersion is ready."
    Write-Host ""
    Write-Host "Try:           gitwise doctor"
    Write-Host "Update later:  uv tool upgrade gitwise-cli"
    Write-Host "Uninstall:     uv tool uninstall gitwise-cli"
} else {
    Write-Host ""
    Write-Host "gitwise installed, but the 'gitwise' command is not yet on PATH."
    Write-Host "uv places tool entry points in: $uvBinDir"
    Write-Host ""
    Write-Host "Pick one:"
    Write-Host "  1. Open a new PowerShell window (PATH will refresh automatically)."
    Write-Host "  2. Or add uv's bin directory to your user PATH (one time):"
    Write-Host "       [Environment]::SetEnvironmentVariable('Path', `"$uvBinDir;`$([Environment]::GetEnvironmentVariable('Path', 'User'))`", 'User')"
    Write-Host "  Then open a new PowerShell window."
}
