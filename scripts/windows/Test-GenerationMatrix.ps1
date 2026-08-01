[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArchipelagoPath,
    [string]$PythonPath,
    [string]$ApworldPath,
    [int]$Seed = 20260801,
    [int]$SoloCases = 256,
    [int]$SameGameCases = 3328,
    [int]$SameGameSlots = 8,
    [int]$MixedCases = 384,
    [int]$MixedLotFSlots = 2,
    [string]$ReportPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$apRoot = (Resolve-Path -LiteralPath $ArchipelagoPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $apRoot 'BaseClasses.py') -PathType Leaf)) {
    throw "Not an Archipelago source checkout: $apRoot"
}

if (-not $ApworldPath) {
    $ApworldPath = Join-Path $root 'dist\lotf.apworld'
}
$resolvedApworld = (Resolve-Path -LiteralPath $ApworldPath).Path
$customWorlds = Join-Path $apRoot 'custom_worlds'
New-Item -ItemType Directory -Force -Path $customWorlds | Out-Null
Copy-Item -LiteralPath $resolvedApworld -Destination (Join-Path $customWorlds 'lotf.apworld') -Force

if (-not $PythonPath) {
    $candidate = Join-Path (Split-Path -Parent $root) '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $PythonPath = $candidate
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python -or $python.Source -match 'WindowsApps') {
            throw 'Python was not found. Supply -PythonPath.'
        }
        $PythonPath = $python.Source
    }
}
$pythonExecutable = (Resolve-Path -LiteralPath $PythonPath).Path
if (-not $ReportPath) {
    $ReportPath = Join-Path $root 'test-results\generation-matrix.json'
}

$oldSkipRequirements = $env:SKIP_REQUIREMENTS_UPDATE
try {
    $env:SKIP_REQUIREMENTS_UPDATE = '1'
    & $pythonExecutable (Join-Path $PSScriptRoot '..\common\Test-GenerationMatrix.py') `
        --archipelago-path $apRoot `
        --seed $Seed `
        --solo-cases $SoloCases `
        --same-game-cases $SameGameCases `
        --same-game-slots $SameGameSlots `
        --mixed-cases $MixedCases `
        --mixed-lotf-slots $MixedLotFSlots `
        --report $ReportPath
    if ($LASTEXITCODE -ne 0) {
        throw "Generation matrix failed with exit code $LASTEXITCODE."
    }
} finally {
    $env:SKIP_REQUIREMENTS_UPDATE = $oldSkipRequirements
}

Write-Host "Generation matrix passed. Report: $ReportPath"
