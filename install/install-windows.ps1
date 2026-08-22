<#
.SYNOPSIS
    LR-FolderCraft installer for Windows.

.DESCRIPTION
    Creates a self contained virtual environment, installs LR-FolderCraft with
    the TUI extra and puts an `lrfc` launcher on your PATH. Nothing outside the
    install prefix and the launcher directory is touched.

.PARAMETER Prefix
    Installation directory. Defaults to %LOCALAPPDATA%\LR-FolderCraft.

.PARAMETER BinDir
    Directory for the launcher. Defaults to %LOCALAPPDATA%\Programs\bin.

.PARAMETER NoTui
    Install the command line only, without Textual.

.PARAMETER Uninstall
    Remove a previous installation.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install\install-windows.ps1

.NOTES
    SPDX-License-Identifier: MIT OR GPL-3.0-or-later
#>

[CmdletBinding()]
param(
    [string]$Prefix = "$env:LOCALAPPDATA\LR-FolderCraft",
    [string]$BinDir = "$env:LOCALAPPDATA\Programs\bin",
    [switch]$NoTui,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'
$AppName = 'LR-FolderCraft'
$MinMajor = 3
$MinMinor = 9

function Write-Info { param($Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "[!] $Message" -ForegroundColor Yellow }
function Write-Fail { param($Message) Write-Host "[x] $Message" -ForegroundColor Red; exit 1 }

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# -- uninstall ---------------------------------------------------------------

if ($Uninstall) {
    Write-Info "Removing $AppName"
    if (Test-Path $Prefix) { Remove-Item -Recurse -Force $Prefix }
    foreach ($name in @('lrfc.cmd', 'lr-foldercraft.cmd')) {
        $launcher = Join-Path $BinDir $name
        if (Test-Path $launcher) { Remove-Item -Force $launcher }
    }
    Write-Info 'Removed. Your catalogs, photos, logs and profiles were not touched.'
    Write-Host "    Config and profiles remain in: $env:APPDATA\LR-FolderCraft"
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

Write-Info "Creating the virtual environment in $Prefix"
New-Item -ItemType Directory -Force -Path $Prefix | Out-Null
$VenvDir = Join-Path $Prefix 'venv'
if (Test-Path $VenvDir) {
    Write-Warn 'An existing installation was found and will be replaced.'
    Remove-Item -Recurse -Force $VenvDir
}
$venvArgs = @($PyArgs) + @('-m', 'venv', $VenvDir)
& $PyExe @venvArgs
if ($LASTEXITCODE -ne 0) { Write-Fail 'Could not create the virtual environment.' }

$VenvPy  = Join-Path $VenvDir 'Scripts\python.exe'
$VenvExe = Join-Path $VenvDir 'Scripts\lrfc.exe'

Write-Info 'Updating pip'
& $VenvPy -m pip install --quiet --upgrade pip setuptools wheel

# -- 3. install ----------------------------------------------------------------

$target = if ($NoTui) { $ProjectDir } else { "$ProjectDir[tui]" }
if ($NoTui) { Write-Info "Installing $AppName (command line only)" }
else        { Write-Info "Installing $AppName with the TUI" }
& $VenvPy -m pip install --quiet $target
if ($LASTEXITCODE -ne 0) { Write-Fail 'Installation failed.' }

# -- 4. launcher -----------------------------------------------------------------

Write-Info "Installing the launcher in $BinDir"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$launcherBody = "@echo off`r`n`"$VenvExe`" %*`r`n"
foreach ($name in @('lrfc.cmd', 'lr-foldercraft.cmd')) {
    Set-Content -Path (Join-Path $BinDir $name) -Value $launcherBody -Encoding ASCII
}

# -- 5. PATH -----------------------------------------------------------------------

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($userPath -notlike "*$BinDir*") {
    Write-Info "Adding $BinDir to your user PATH"
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$BinDir", 'User')
    Write-Warn 'Open a new terminal window for the PATH change to take effect.'
}

# -- 6. verify -----------------------------------------------------------------------

Write-Info 'Verifying the installation'
& $VenvExe --version
if ($LASTEXITCODE -ne 0) { Write-Fail 'The installed command did not start.' }

Write-Host ''
Write-Info "$AppName is installed."
Write-Host "    Command      : $BinDir\lrfc.cmd"
Write-Host "    Environment  : $VenvDir"
Write-Host "    Logs         : $env:LOCALAPPDATA\LR-FolderCraft\logs"
Write-Host ''
Write-Host @'
Next steps:

    lrfc info D:\Photos\Catalog.lrcat          inspect a catalog, read only
    lrfc presets                               see the ready made structures
    lrfc plan D:\Photos\Catalog.lrcat -s day   see what would happen
    lrfc tui                                   interactive interface

Quit Lightroom Classic before running 'lrfc apply'.
'@
