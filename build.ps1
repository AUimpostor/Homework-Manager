# Homework Manager build script
# Copyright (C) 2026 AUimpostor <auimpostor@outlook.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This script is distributed under the GNU GPL version 3 or (at your option) any later version.

param(
    [string]$OutputDirectory = "release"
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputDir = Join-Path $ProjectDir $OutputDirectory
$BuildDir = Join-Path $ProjectDir "build"
$TkruntimeDir = Join-Path $BuildDir "tk-runtime"
$LicenseBundleDir = Join-Path $BuildDir "distribution-licenses"
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $PythonCommand) {
    throw "Python was not found. Install Python and add it to PATH."
}
& $PythonCommand.Source -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "当前 Python 没有安装 PyInstaller，请先执行: python -m pip install pyinstaller"
}

function Invoke-CheckedCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code: $LASTEXITCODE"
    }
}

$PythonRoot = (& $PythonCommand.Source -c "import sys; print(sys.prefix)").Trim()
$TclRoot = Join-Path $PythonRoot "tcl"
$TclZip = Get-ChildItem $TclRoot -Filter "libtcl*.zip" | Select-Object -First 1
$TkZip = Get-ChildItem $TclRoot -Filter "libtk*.zip" | Select-Object -First 1

if (-not $TclZip -or -not $TkZip) {
    throw "Python Tcl/Tk zip resources were not found. Install Python with tkinter."
}

Write-Host "Preparing Tcl/Tk runtime resources..."
Remove-Item $TkruntimeDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path `
    (Join-Path $TkruntimeDir "tcl-temp"), `
    (Join-Path $TkruntimeDir "tk-temp"), `
    (Join-Path $TkruntimeDir "_tcl_data"), `
    (Join-Path $TkruntimeDir "_tk_data") | Out-Null

Expand-Archive -LiteralPath $TclZip.FullName -DestinationPath (Join-Path $TkruntimeDir "tcl-temp")
Expand-Archive -LiteralPath $TkZip.FullName -DestinationPath (Join-Path $TkruntimeDir "tk-temp")
Copy-Item (Join-Path $TkruntimeDir "tcl-temp\tcl_library\*") `
    (Join-Path $TkruntimeDir "_tcl_data") -Recurse -Force
Copy-Item (Join-Path $TkruntimeDir "tk-temp\tk_library\*") `
    (Join-Path $TkruntimeDir "_tk_data") -Recurse -Force

Remove-Item $LicenseBundleDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path `
    $LicenseBundleDir, `
    (Join-Path $LicenseBundleDir "third_party_licenses"), `
    (Join-Path $LicenseBundleDir "tcl"), `
    (Join-Path $LicenseBundleDir "tk") | Out-Null
Copy-Item (Join-Path $ProjectDir "LICENSE.md") $LicenseBundleDir -Force
Copy-Item (Join-Path $ProjectDir "THIRD_PARTY_NOTICES.md") $LicenseBundleDir -Force
Copy-Item (Join-Path $ProjectDir "third_party_licenses\*") (Join-Path $LicenseBundleDir "third_party_licenses") -Force
$PythonLicense = Join-Path $PythonRoot "LICENSE.txt"
if (Test-Path $PythonLicense) { Copy-Item $PythonLicense (Join-Path $LicenseBundleDir "python-LICENSE.txt") -Force }
foreach ($runtimeLicense in @(
    @{ Source = (Join-Path $TkruntimeDir "_tcl_data"); Destination = (Join-Path $LicenseBundleDir "tcl") },
    @{ Source = (Join-Path $TkruntimeDir "_tk_data"); Destination = (Join-Path $LicenseBundleDir "tk") }
)) {
    Get-ChildItem -LiteralPath $runtimeLicense.Source -File -Recurse |
        Where-Object { $_.Name -match '^license\.terms$' } |
        ForEach-Object { Copy-Item $_.FullName $runtimeLicense.Destination -Force }
}

Write-Host "Cleaning the old output directory..."
Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue

$PyInstallerArguments = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--icon", (Join-Path $ProjectDir "icon.ico"),
    "--add-data", "$(Join-Path $ProjectDir 'icon.ico');.",
    "--add-data", "$(Join-Path $TkruntimeDir '_tcl_data');_tcl_data",
    "--add-data", "$(Join-Path $TkruntimeDir '_tk_data');_tk_data",
    "--add-data", "$LicenseBundleDir;distribution-licenses",
    "--hidden-import", "display",
    "--hidden-import", "editor",
    "--hidden-import", "dashboard",
    "--hidden-import", "subscriptionManager",
    "--hidden-import", "appIdentity",
    "--hidden-import", "preview",
    "--hidden-import", "subscriptionService",
    "--hidden-import", "config",
    "--hidden-import", "runtime",
    "--hidden-import", "pystray",
    "--hidden-import", "winotify",
    "--name", "Homework Manager",
    "--distpath", $OutputDir,
    "--workpath", (Join-Path $BuildDir "onefile"),
    "--specpath", $BuildDir,
    (Join-Path $ProjectDir "main.py")
)

Write-Host "Building Homework Manager.exe..."
$BuildLog = Join-Path $ProjectDir "build.log"
$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $PythonCommand.Source -m PyInstaller @PyInstallerArguments 2>&1 |
    ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            $_.ToString()
        } else {
            $_
        }
    } | Tee-Object -FilePath $BuildLog
$PyInstallerExitCode = $LASTEXITCODE
$ErrorActionPreference = $PreviousErrorActionPreference
if ($PyInstallerExitCode -ne 0) {
    throw "PyInstaller failed. See: $BuildLog"
}

$MainAppDir = Join-Path $OutputDir "Homework Manager"
$Executable = Join-Path $MainAppDir "Homework Manager.exe"
if (-not (Test-Path $Executable)) {
    throw "Build completed but the executable was not found: $Executable"
}

# --- Uninstaller (onefile, alongside the main executable) ---
$UninstallerWorkDir = Join-Path $BuildDir "uninstall-onefile"
Remove-Item $UninstallerWorkDir -Recurse -Force -ErrorAction SilentlyContinue

$UninstallerArguments = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--icon", (Join-Path $ProjectDir "icon.ico"),
    "--add-data", "$(Join-Path $ProjectDir 'icon.ico');.",
    "--add-data", "$(Join-Path $TkruntimeDir '_tcl_data');_tcl_data",
    "--add-data", "$(Join-Path $TkruntimeDir '_tk_data');_tk_data",
    "--name", "Uninstall",
    "--distpath", $MainAppDir,
    "--workpath", $UninstallerWorkDir,
    "--specpath", $BuildDir,
    (Join-Path $ProjectDir "uninstall.py")
)

Write-Host "Building Uninstall.exe (onefile)..."
$PreviousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $PythonCommand.Source -m PyInstaller @UninstallerArguments 2>&1 |
    ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            $_.ToString()
        } else {
            $_
        }
    } | Tee-Object -FilePath $BuildLog -Append
$PyInstallerExitCode = $LASTEXITCODE
$ErrorActionPreference = $PreviousErrorActionPreference
if ($PyInstallerExitCode -ne 0) {
    throw "Uninstaller build failed. See: $BuildLog"
}

$Uninstaller = Join-Path $MainAppDir "Uninstall.exe"
if (-not (Test-Path $Uninstaller)) {
    throw "Uninstaller build completed but Uninstall.exe was not found: $Uninstaller"
}

Set-Content (Join-Path $OutputDir "build-version.txt") -Value (
    "Built: {0}`nSource: {1}`nExecutable: {2}`nUninstaller: {3}" -f (Get-Date -Format o), $ProjectDir, $Executable, $Uninstaller
) -Encoding UTF8

Write-Host ""
Write-Host "Build completed: $Executable" -ForegroundColor Green
Write-Host "Uninstaller: $Uninstaller" -ForegroundColor Green
Write-Host "Config file: $(Join-Path (Join-Path $OutputDir 'Homework Manager\data') 'config.json')"
Write-Host "Assignment file: $(Join-Path (Join-Path $OutputDir 'Homework Manager\data') 'assignment.json')"
