<#
.SYNOPSIS
    LR-CompanionSuite installer for Windows.

.DESCRIPTION
    Creates a self contained virtual environment, installs the LR-CompanionSuite with
    the TUI extra and puts an `lrfc` launcher on your PATH. Nothing outside the
    install prefix and the launcher directory is touched.

.PARAMETER Prefix
    Installation directory. Defaults to %LOCALAPPDATA%\LR-CompanionSuite.

.PARAMETER BinDir
    Directory for the launcher. Defaults to %LOCALAPPDATA%\Programs\bin.

.PARAMETER NoTui
    Install the command line only, without Textual.

.PARAMETER WithGui
    Also install PySide6 so that `lrfc gui` works. About 100 MB.

.PARAMETER NoGui
    Never ask about the graphical interface.

.PARAMETER Check
    Verify an existing installation and repair whatever is missing.

.PARAMETER Recreate
    Build the virtual environment from scratch instead of reusing it.

.PARAMETER Uninstall
    Remove a previous installation.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install\install-windows.ps1

.NOTES
    SPDX-License-Identifier: MIT OR GPL-3.0-or-later
#>

[CmdletBinding()]
param(
    [string]$Prefix = "$env:LOCALAPPDATA\LR-CompanionSuite",
    [string]$BinDir = "$env:LOCALAPPDATA\Programs\bin",
    [switch]$NoTui,
    [switch]$WithGui,
    [switch]$NoGui,
    [switch]$Recreate,
    [switch]$Check,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$AppName = 'LR-CompanionSuite'
$MinMajor = 3
$MinMinor = 9

function Write-Info { param($Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "[!] $Message" -ForegroundColor Yellow }
function Write-Fail { param($Message) Write-Host "[x] $Message" -ForegroundColor Red; exit 1 }

# Each optional interface is one importable module and one pip requirement.
# Everything below drives off this table, so a component can never be installed
# without being verified, or advertised without being installed.
$Components = @{
    tui = @{ Module = 'textual';           Requirement = 'textual>=0.47';            Dist = 'textual';            Command = 'lrfc tui' }
    gui = @{ Module = 'PySide6.QtWidgets'; Requirement = 'PySide6-Essentials>=6.5';  Dist = 'PySide6-Essentials'; Command = 'lrfc gui' }
}

# File remembering which optional components this installation wants. Without
# it a repair run cannot tell "the GUI was never asked for" from "the GUI was
# installed and is now broken" -- both simply fail to import.
function Get-ComponentsFile { return (Join-Path $Prefix 'components') }

function Save-Components {
    param($Names)
    Set-Content -Path (Get-ComponentsFile) -Value ($Names -join "`n") -Encoding ASCII
}

function Get-SavedComponents {
    $file = Get-ComponentsFile
    if (Test-Path $file) {
        return @(Get-Content $file | Where-Object { $_.Trim() })
    }
    return $null
}

function Test-Component {
    param($Name)
    & $script:VenvPy -c "import $($Components[$Name].Module)" 2>$null
    return $LASTEXITCODE -eq 0
}

function Get-ComponentVersion {
    param($Name)
    $dist = $Components[$Name].Dist
    $out = & $script:VenvPy -c "
try:
    from importlib.metadata import version; print(version('$dist'))
except Exception:
    pass" 2>$null
    return ($out | Out-String).Trim()
}

# Install or update a component, then confirm it imports. A present but
# out-of-date module counts as work to do: half the reason to re-run an
# installer is to refresh what has aged.
function Install-Component {
    param($Name)
    $before = Get-ComponentVersion $Name
    if ((Test-Component $Name) -and $Check) {
        Write-Info "$Name`: working (version $(if ($before) { $before } else { '?' }))"
        return $true
    }
    if ($before) { Write-Info "$Name`: updating $($Components[$Name].Requirement) (have $before)" }
    else         { Write-Info "$Name`: installing $($Components[$Name].Requirement)" }
    & $script:VenvPy -m pip install --quiet --upgrade $Components[$Name].Requirement
    if ($LASTEXITCODE -ne 0) { Write-Warn "$Name`: installation failed"; return $false }
    if (-not (Test-Component $Name)) {
        Write-Warn "$Name`: installed but $($Components[$Name].Module) still does not import"
        return $false
    }
    $after = Get-ComponentVersion $Name
    if ($before -and $before -ne $after) { Write-Info "$Name`: updated $before -> $after" }
    elseif ($before)                     { Write-Info "$Name`: already up to date ($after)" }
    else                                 { Write-Info "$Name`: installed and verified ($after)" }
    return $true
}

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# -- uninstall ---------------------------------------------------------------

if ($Uninstall) {
    Write-Info "Removing $AppName"
    if (Test-Path $Prefix) { Remove-Item -Recurse -Force $Prefix }
    foreach ($name in @('lrcs.cmd', 'lrfc.cmd', 'lrms.cmd', 'lr-companion-suite.cmd')) {
        $launcher = Join-Path $BinDir $name
        if (Test-Path $launcher) { Remove-Item -Force $launcher }
    }
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -and $userPath.Split(';') -contains $BinDir) {
        $kept = ($userPath.Split(';') | Where-Object { $_ -ne $BinDir }) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $kept, 'User')
        Write-Info "Removed $BinDir from your user PATH"
    }
    Write-Info 'Removed. Your catalogs, photos, logs and profiles were not touched.'
    Write-Host "    Config and profiles remain in: $env:APPDATA\LR-CompanionSuite"
    exit 0
}

# -- 1. find a suitable Python ------------------------------------------------

function Find-Python {
    $candidates = @()
    # The Windows launcher knows about every installed version.
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in @('3.13', '3.12', '3.11', '3.10', '3.9')) {
            $candidates += ,@('py', @("-$version"))
        }
    }
    $candidates += ,@('python', @())
    $candidates += ,@('python3', @())

    foreach ($candidate in $candidates) {
        $exe  = $candidate[0]
        $args = $candidate[1]
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        $check = @($args) + @('-c', "import sys; sys.exit(0 if sys.version_info >= ($MinMajor, $MinMinor) else 1)")
        & $exe @check 2>$null
        if ($LASTEXITCODE -eq 0) { return ,@($exe, $args) }
    }
    return $null
}

Write-Info "Looking for Python >= $MinMajor.$MinMinor"
$python = Find-Python
if (-not $python) {
    Write-Fail @"
No Python $MinMajor.$MinMinor or newer was found.

Install it from https://www.python.org/downloads/windows/ or from the
Microsoft Store, and tick "Add python.exe to PATH" during setup.
"@
}
$PyExe  = $python[0]
$PyArgs = $python[1]
$versionText = & $PyExe @PyArgs -c "import sys; print(sys.version.split()[0])"
Write-Info "Using $PyExe $PyArgs (Python $versionText)"

& $PyExe @PyArgs -c "import sqlite3" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Fail 'This Python has no sqlite3 support, which is required to read Lightroom catalogs.'
}

# -- 2. create the virtual environment ----------------------------------------

New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
$VenvDir = Join-Path $Prefix 'venv'
$VenvPy  = Join-Path $VenvDir 'Scripts\python.exe'
$VenvExe = Join-Path $VenvDir 'Scripts\lrfc.exe'
$script:VenvPy = $VenvPy

if ((Test-Path $VenvDir) -and $Recreate) {
    Write-Warn 'Rebuilding the existing environment from scratch.'
    Remove-Item -Recurse -Force $VenvDir
}
if (Test-Path $VenvPy) {
    # Reusing the environment is what makes "add the graphical interface later"
    # a short job instead of a full reinstall.
    Write-Info "Reusing the environment in $VenvDir"
} else {
    Write-Info "Creating the virtual environment in $Prefix"
    $venvArgs = @($PyArgs) + @('-m', 'venv', $VenvDir)
    & $PyExe @venvArgs
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Could not create the virtual environment.' }
}

if (-not $Check) {
    Write-Info 'Updating pip'
    & $VenvPy -m pip install --quiet --upgrade pip setuptools wheel
}

# -- 3. install ----------------------------------------------------------------

$wantTui = -not $NoTui
$wantGui = $WithGui

if ($Check) {
    Write-Info 'Checking the existing installation'
    if (-not (Test-Path $VenvPy)) { Write-Fail "No installation found in $Prefix -- run without -Check first" }
    # Repair exactly the set this installation was set up with. Asking which
    # modules import right now would treat a broken component as an absent one.
    $saved = Get-SavedComponents
    if ($null -ne $saved) {
        $wantTui = $saved -contains 'tui'
        if (-not $WithGui -and -not $NoGui) { $wantGui = $saved -contains 'gui' }
    } else {
        Write-Warn 'No record of what was installed; checking what is present.'
        $wantTui = $wantTui -and (Test-Component 'tui')
        if (-not $WithGui -and -not $NoGui) { $wantGui = Test-Component 'gui' }
    }
} else {
    # Discovering -WithGui from a help text is not a plan, so ask when nobody
    # said either way and there is someone to ask.
    if (-not $WithGui -and -not $NoGui) {
        if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
            Write-Host ''
            Write-Host 'Also install the graphical interface (lrfc gui)?'
            $answer = Read-Host 'It needs PySide6, about 100 MB to download. [y/N]'
            $wantGui = $answer -match '^[yYjJ]'
        }
    }
    Write-Info "Installing $AppName"
    if ($wantGui) { Write-Info 'PySide6 is about 100 MB -- this takes a moment' }
    # --upgrade so that re-running the installer also refreshes anything that
    # has gone out of date, which is half of what people re-run it for.
    & $VenvPy -m pip install --quiet --upgrade $ProjectDir
    if ($LASTEXITCODE -ne 0) { Write-Fail 'Installation failed.' }
}

$failed = @()
if ($wantTui -and -not (Install-Component 'tui')) { $failed += 'tui' }
if ($wantGui -and -not (Install-Component 'gui')) { $failed += 'gui' }
if (-not $Check) {
    $chosen = @()
    if ($wantTui) { $chosen += 'tui' }
    if ($wantGui) { $chosen += 'gui' }
    Save-Components $chosen
}

# -- 4. launcher -----------------------------------------------------------------

Write-Info "Installing the launcher in $BinDir"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$launcherBody = "@echo off`r`n`"$VenvExe`" %*`r`n"
foreach ($name in @('lrcs.cmd', 'lrfc.cmd', 'lrms.cmd', 'lr-companion-suite.cmd')) {
    Set-Content -Path (Join-Path $BinDir $name) -Value $launcherBody -Encoding ASCII
}

# -- 5. PATH -----------------------------------------------------------------------

# An installation that reports success but leaves an un-runnable command is not
# finished, so the launcher directory goes on the user PATH here rather than in
# an instruction the user has to follow.
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = if ($userPath) { $userPath.Split(';') } else { @() }
if ($entries -contains $BinDir) {
    Write-Info "$BinDir is already on your user PATH."
} else {
    Write-Info "Adding $BinDir to your user PATH"
    $joined = if ($userPath) { "$userPath;$BinDir" } else { $BinDir }
    [Environment]::SetEnvironmentVariable('Path', $joined, 'User')
    Write-Warn 'A running terminal keeps its old PATH. Open a new window before using lrfc.'
}

# -- 6. verify -----------------------------------------------------------------------

Write-Info 'Verifying the installation'
& $VenvExe --version
if ($LASTEXITCODE -ne 0) { Write-Fail 'The installed command did not start.' }

Write-Host ''
Write-Info "$AppName is installed."
Write-Host "    Command      : $BinDir\lrfc.cmd"
Write-Host "    Environment  : $VenvDir"
Write-Host "    Logs         : $env:LOCALAPPDATA\LR-CompanionSuite\logs"
$working = @('cli') + @('tui','gui' | Where-Object { Test-Component $_ })
Write-Host "    Interfaces   : $($working -join ' ')"

foreach ($name in $failed) {
    Write-Warn "$($Components[$name].Command) is not available: $($Components[$name].Module) could not be installed."
    Write-Host "    Try it by hand:  $VenvPy -m pip install `"$($Components[$name].Requirement)`""
}

Write-Host ''
Write-Host 'Next steps:'
Write-Host ''
Write-Host '    lrfc info D:\Photos\Catalog.lrcat          inspect a catalog, read only'
Write-Host '    lrfc presets                               see the ready made structures'
Write-Host '    lrfc plan D:\Photos\Catalog.lrcat -s day   see what would happen'
if (Test-Component 'tui') { Write-Host '    lrfc tui                                   interactive text interface' }
if (Test-Component 'gui') {
    Write-Host '    lrfc gui                                   graphical interface'
} else {
    Write-Host ''
    Write-Host 'The graphical interface is not installed. To add it:'
    Write-Host "    powershell -ExecutionPolicy Bypass -File $($MyInvocation.MyCommand.Path) -WithGui"
}
Write-Host ''
Write-Host "Quit Lightroom Classic before running 'lrfc apply'."
