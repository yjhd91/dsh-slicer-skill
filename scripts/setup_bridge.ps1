# setup_bridge.ps1 — make a 3D Slicer installation load this skill's bridge at startup.
#
# Usage:
#   .\setup_bridge.ps1 -SlicerDir "D:\Slicer 5.12.4"
#   .\setup_bridge.ps1 -SlicerDir "D:\Slicer 5.12.4" -BridgeDir "D:\SlicerModules\bridge"
#
# What it does:
#   1. copies bridge_autoload.py into -BridgeDir (default: <skill>\bridge)
#   2. patches that Slicer's bin\SlicerLauncherSettings.ini so every launch passes
#      --python-script <bridge_autoload.py>   (backup kept as *.bak_before_bridge)
#
# Revert: restore the .bak_before_bridge file.

param(
    [Parameter(Mandatory = $true)][string]$SlicerDir,
    [string]$BridgeDir
)

$ErrorActionPreference = 'Stop'

$skillDir = Split-Path -Parent $PSScriptRoot
if (-not $BridgeDir) { $BridgeDir = Join-Path $skillDir 'bridge' }

$ini = Join-Path $SlicerDir 'bin\SlicerLauncherSettings.ini'
if (-not (Test-Path $ini)) {
    throw "SlicerLauncherSettings.ini not found under '$SlicerDir'. Is that a 3D Slicer install directory?"
}

New-Item -ItemType Directory -Force -Path $BridgeDir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'bridge_autoload.py') $BridgeDir -Force
$autoload = Join-Path $BridgeDir 'bridge_autoload.py'

# Quote only when needed; CTKAppLauncher splits arguments on spaces.
$argValue = if ($autoload -match '\s') { '--python-script "' + $autoload + '"' } else { '--python-script ' + $autoload }

$txt = Get-Content $ini -Raw
if ($txt -match '(?m)^arguments=.*bridge_autoload') {
    Write-Host "Already configured; updating the path to $autoload"
    $new = $txt -replace '(?m)^arguments=.*$', ('arguments=' + $argValue)
} else {
    $new = $txt -replace '(?m)^arguments=\s*$', ('arguments=' + $argValue)
    if ($new -eq $txt) {
        throw "Could not find an empty 'arguments=' line in the [Application] section of $ini"
    }
}

if (-not (Test-Path "$ini.bak_before_bridge")) {
    Copy-Item $ini "$ini.bak_before_bridge" -Force
}
[System.IO.File]::WriteAllText($ini, $new, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "bridge dir : $BridgeDir"
Write-Host "autoload   : $autoload"
Write-Host "patched    : $ini"
Write-Host ""
Write-Host "Next: start 3D Slicer normally, then run:"
Write-Host ('  python "' + (Join-Path $PSScriptRoot 'slicer.py') + '" --status')
