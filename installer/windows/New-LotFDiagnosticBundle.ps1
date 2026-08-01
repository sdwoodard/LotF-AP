[CmdletBinding()]
param(
    [string]$MultiworldPath,
    [string]$PlayerYamlPath,
    [string]$GamePath,
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$dataRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago'
if (-not (Test-Path -LiteralPath $dataRoot -PathType Container)) {
    throw "No LotF Archipelago diagnostic data exists at $dataRoot"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path (Get-Location) ("LotF-AP-Diagnostics-{0}.zip" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $OutputPath) {
    throw "Output already exists: $OutputPath"
}

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("LotF-AP-Diagnostics-" + [guid]::NewGuid().ToString('N'))
$resolvedTemporary = [System.IO.Path]::GetFullPath($temporary)
if (-not $resolvedTemporary.StartsWith([System.IO.Path]::GetTempPath(), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unexpected temporary path: $resolvedTemporary"
}
New-Item -ItemType Directory -Force -Path $resolvedTemporary | Out-Null

try {
    foreach ($directory in @('logs', 'recovery', 'bridge')) {
        $source = Join-Path $dataRoot $directory
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $resolvedTemporary $directory) -Recurse
        }
    }
    $state = Join-Path $dataRoot 'state.txt'
    if (Test-Path -LiteralPath $state) {
        Copy-Item -LiteralPath $state -Destination $resolvedTemporary
    }

    $attachments = Join-Path $resolvedTemporary 'attachments'
    New-Item -ItemType Directory -Force -Path $attachments | Out-Null
    foreach ($entry in @(
        @{ Label = 'multiworld'; Path = $MultiworldPath },
        @{ Label = 'player-yaml'; Path = $PlayerYamlPath }
    )) {
        if (-not $entry.Path) { continue }
        $resolved = (Resolve-Path -LiteralPath $entry.Path).Path
        Copy-Item -LiteralPath $resolved -Destination (Join-Path $attachments (Split-Path -Leaf $resolved))
    }

    $gameVersion = 'not supplied'
    $gameHash = 'not supplied'
    $gameSize = 'not supplied'
    $gameModifiedUtc = 'not supplied'
    if ($GamePath) {
        $executable = Join-Path $GamePath 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'
        if (Test-Path -LiteralPath $executable) {
            $gameItem = Get-Item -LiteralPath $executable
            $gameVersion = $gameItem.VersionInfo.FileVersion
            if (-not $gameVersion) { $gameVersion = 'not reported by executable metadata' }
            $gameHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash
            $gameSize = $gameItem.Length
            $gameModifiedUtc = $gameItem.LastWriteTimeUtc.ToString('o')
            foreach ($ue4ssLog in @(
                (Join-Path $GamePath 'LOTF2\Binaries\Win64\UE4SS.log'),
                (Join-Path $GamePath 'LOTF2\Binaries\Win64\ue4ss\UE4SS.log')
            )) {
                if (Test-Path -LiteralPath $ue4ssLog) {
                    $logName = if ($ue4ssLog -match '\\ue4ss\\') { 'UE4SS-current-layout.log' } else { 'UE4SS.log' }
                    Copy-Item -LiteralPath $ue4ssLog -Destination (Join-Path $resolvedTemporary $logName)
                }
            }
        }
    }

    $versionFile = @(
        (Join-Path $PSScriptRoot 'VERSION'),
        (Join-Path $PSScriptRoot '..\VERSION'),
        (Join-Path $PSScriptRoot '..\..\VERSION')
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    $clientVersion = if ($versionFile -and (Test-Path -LiteralPath $versionFile)) {
        (Get-Content -Raw -LiteralPath $versionFile).Trim()
    } else {
        'unknown'
    }
    @(
        "Created UTC: $([DateTime]::UtcNow.ToString('o'))"
        "LotF AP version: $clientVersion"
        "Game file version: $gameVersion"
        "Game executable SHA-256: $gameHash"
        "Game executable size: $gameSize"
        "Game executable modified UTC: $gameModifiedUtc"
        "Windows: $([Environment]::OSVersion.VersionString)"
        "Multiworld attached: $([bool]$MultiworldPath)"
        "Player YAML attached: $([bool]$PlayerYamlPath)"
        ''
        'This bundle intentionally does not include any Lords of the Fallen save file.'
        'Review optional YAML and multiworld attachments before sharing them.'
    ) | Set-Content -LiteralPath (Join-Path $resolvedTemporary 'SUMMARY.txt') -Encoding UTF8

    Compress-Archive -Path (Join-Path $resolvedTemporary '*') -DestinationPath $OutputPath -CompressionLevel Optimal
    Write-Host "Created diagnostic bundle: $OutputPath"
    Write-Warning 'Review the archive before sharing. Add a written description of what happened and when.'
} finally {
    if (Test-Path -LiteralPath $resolvedTemporary) {
        Remove-Item -LiteralPath $resolvedTemporary -Recurse -Force
    }
}
