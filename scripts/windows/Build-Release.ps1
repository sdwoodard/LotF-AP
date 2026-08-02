[CmdletBinding()]
param(
    [switch]$SkipValidation,
    [string]$GamePath,
    [string]$RetocPath,
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$version = (Get-Content -Raw -LiteralPath (Join-Path $root 'VERSION')).Trim()
if (-not $SkipValidation) {
    & (Join-Path $PSScriptRoot 'Test-Repository.ps1') -GamePath $GamePath -RetocPath $RetocPath -PythonPath $PythonPath
}

$build = Join-Path $root 'build'
$dist = Join-Path $root 'dist'
foreach ($directory in @($build, $dist)) {
    $resolved = [System.IO.Path]::GetFullPath($directory)
    if (-not $resolved.StartsWith($root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean unexpected path: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $resolved | Out-Null
}

$apworldStage = Join-Path $build 'apworld\lotf'
New-Item -ItemType Directory -Force -Path $apworldStage | Out-Null
Copy-Item -Path (Join-Path $root 'worlds\lotf\*') -Destination $apworldStage -Recurse
Get-ChildItem -LiteralPath $apworldStage -Directory -Recurse -Filter '__pycache__' | Remove-Item -Recurse -Force
$apworldZip = Join-Path $build 'lotf.zip'
Compress-Archive -LiteralPath (Join-Path $build 'apworld\lotf') -DestinationPath $apworldZip -CompressionLevel Optimal
$apworld = Join-Path $dist 'lotf.apworld'
Move-Item -LiteralPath $apworldZip -Destination $apworld

$packageStage = Join-Path $build "package\LotF-Archipelago-$version"
New-Item -ItemType Directory -Force -Path $packageStage | Out-Null
Copy-Item -LiteralPath $apworld -Destination (Join-Path $packageStage 'lotf.apworld')
Copy-Item -Path (Join-Path $root 'installer\windows\*.ps1') -Destination $packageStage
Copy-Item -Path (Join-Path $root 'installer\windows\*.cmd') -Destination $packageStage
Copy-Item -Path (Join-Path $root 'installer\linux\*.sh') -Destination $packageStage
Copy-Item -LiteralPath (Join-Path $root 'README.md') -Destination (Join-Path $packageStage 'README.md')
Copy-Item -LiteralPath (Join-Path $root 'CHANGELOG.md') -Destination (Join-Path $packageStage 'CHANGELOG.md')
Copy-Item -LiteralPath (Join-Path $root 'LICENSE') -Destination (Join-Path $packageStage 'LICENSE')
Copy-Item -LiteralPath (Join-Path $root 'VERSION') -Destination (Join-Path $packageStage 'VERSION')
Copy-Item -LiteralPath (Join-Path $root 'player-options\Lords of the Fallen.yaml') -Destination $packageStage
$packageDocs = Join-Path $packageStage 'docs'
New-Item -ItemType Directory -Force -Path $packageDocs | Out-Null
Copy-Item -Path (Join-Path $root 'docs\*') -Destination $packageDocs -Recurse
$payload = Join-Path $packageStage 'game-mod\LotFArchipelago'
New-Item -ItemType Directory -Force -Path $payload | Out-Null
Copy-Item -Path (Join-Path $root 'game-mod\LotFArchipelago\*') -Destination $payload -Recurse

$linuxPackageParent = Join-Path $build 'package-linux'
New-Item -ItemType Directory -Force -Path $linuxPackageParent | Out-Null
Copy-Item -LiteralPath $packageStage -Destination $linuxPackageParent -Recurse
$linuxPackageStage = Join-Path $linuxPackageParent "LotF-Archipelago-$version"
Get-ChildItem -LiteralPath $packageStage -File -Filter '*.sh' | Remove-Item -Force
Get-ChildItem -LiteralPath $linuxPackageStage -File -Filter '*.ps1' | Remove-Item -Force
Get-ChildItem -LiteralPath $linuxPackageStage -File -Filter '*.cmd' | Remove-Item -Force

$packageZip = Join-Path $dist "LotF-Archipelago-$version-win64.zip"
Compress-Archive -LiteralPath $packageStage -DestinationPath $packageZip -CompressionLevel Optimal
$linuxPackageZip = Join-Path $dist "LotF-Archipelago-$version-linux.zip"
Compress-Archive -LiteralPath $linuxPackageStage -DestinationPath $linuxPackageZip -CompressionLevel Optimal

Write-Host "Built release artifacts in $dist"
