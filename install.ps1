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
    # Optional integrity verification: set $env:UV_INSTALLER_SHA256 to pin the
    # expected SHA-256 of the uv installer. When set, download to a temp file,
    # verify the hash, and execute only on match; otherwise abort. When unset,
    # fall back to the documented irm|iex TOFU default.
    $url = $env:UV_INSTALLER_URL
    if (-not $url) { $url = "https://astral.sh/uv/install.ps1" }
    if ($env:UV_INSTALLER_SHA256) {
        $tmp = [System.IO.Path]::GetTempFileName()
        try {
            Invoke-RestMethod -Uri $url -OutFile $tmp
            $actual = (Get-FileHash -Algorithm SHA256 -Path $tmp).Hash.ToLower()
            if ($actual -ne $env:UV_INSTALLER_SHA256.ToLower()) {
                throw "uv installer SHA-256 mismatch (expected $($env:UV_INSTALLER_SHA256), got $actual)"
            }
            & powershell -ExecutionPolicy ByPass -File $tmp
        }
        finally {
            Remove-Item $tmp -ErrorAction SilentlyContinue
        }
    }
    else {
        & powershell -ExecutionPolicy ByPass -c "irm $url | iex"
    }
}

function Refresh-SessionPath {
    # The uv installer writes to the User PATH env var, but we cannot rebuild
    # $env:Path from the registry here — that would discard session-specific
    # PATH additions (e.g. tool caches) and reverse the standard Windows PATH
    # evaluation order. Prepend the uv bin directory to the live session PATH
    # instead; subsequent `Get-Command uv` calls will find it.
    $uvBinDir = Join-Path $env:USERPROFILE ".local\bin"
    # Exact-match PATH entries (split on ';') instead of substring match,
    # so a different entry like "C:\foo\.local\bin-other" does not suppress
    # the prepend when "C:\foo\.local\bin" is actually missing.
    $pathEntries = @($env:Path -split ';' | ForEach-Object { $_.Trim() }) | Where-Object { $_ }
    if ($pathEntries -notcontains $uvBinDir) {
        $env:Path = "$uvBinDir;$env:Path"
    }
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
        # Write-Error would terminate immediately under $ErrorActionPreference=Stop,
        # making the exit 2 unreachable. Use Write-Host -ForegroundColor Red first.
        Write-Host "Error: Invalid -Version '$Version'. Expected X.Y.Z." -ForegroundColor Red
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
        Write-Host "Error: uv installer finished but 'uv' is not on PATH." -ForegroundColor Red
        Write-Host "Open a new PowerShell window and re-run, or add manually:" -ForegroundColor Red
        Write-Host "  [Environment]::SetEnvironmentVariable('Path', `"$env:USERPROFILE\.local\bin;`$([Environment]::GetEnvironmentVariable('Path', 'User'))`", 'User')" -ForegroundColor Red
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
    Write-Host "Error: uv tool install failed with exit code $LASTEXITCODE." -ForegroundColor Red
    exit 1
}

# --- Step 5: verify and print PATH guidance ---
$uvBinDir = Join-Path $env:USERPROFILE ".local\bin"
$gitwiseCmd = Get-Command gitwise -ErrorAction SilentlyContinue
if ($gitwiseCmd) {
    $installedVersion = & gitwise --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: gitwise command was found, but '--version' failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit 1
    }
    if (-not $installedVersion) { $installedVersion = "gitwise (version unknown)" }
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
