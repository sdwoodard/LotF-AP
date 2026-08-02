[CmdletBinding(SupportsShouldProcess)]
param([string]$GamePath, [switch]$NoGui)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$dataRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago'
$configPath = Join-Path $dataRoot 'install.json'
$launcherLog = Join-Path $dataRoot 'logs\lotf-launcher.log'

function Test-GameRoot([string]$Path) {
    return $Path -and (Test-Path -LiteralPath (Join-Path $Path 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'))
}

function Write-UninstallLog([string]$Message) {
    $directory = Split-Path -Parent $launcherLog
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    Add-Content -LiteralPath $launcherLog -Value ("{0} {1}" -f [DateTime]::UtcNow.ToString('o'), $Message) -Encoding UTF8
}

try {
    if (-not $GamePath) {
        if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
            throw 'No saved installation was found. Supply -GamePath only when recovering an installation whose settings file was removed.'
        }
        $configuration = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
        $GamePath = [string]$configuration.game_path
    }
    if (-not (Test-GameRoot $GamePath)) {
        throw "The saved Lords of the Fallen folder is no longer valid: $GamePath"
    }

    $gameRoot = (Resolve-Path -LiteralPath $GamePath).Path
    $win64 = (Resolve-Path -LiteralPath (Join-Path $gameRoot 'LOTF2\Binaries\Win64')).Path
    foreach ($modsRoot in @((Join-Path $win64 'ue4ss\Mods'), (Join-Path $win64 'Mods'))) {
        $target = Join-Path $modsRoot 'LotFArchipelago'
        $resolvedRoot = [System.IO.Path]::GetFullPath($modsRoot).TrimEnd('\')
        $resolvedTarget = [System.IO.Path]::GetFullPath($target)
        if (-not $resolvedTarget.StartsWith($resolvedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove an unexpected path: $resolvedTarget"
        }
        if ((Test-Path -LiteralPath $target) -and $PSCmdlet.ShouldProcess($target, 'Remove LotFArchipelago')) {
            Remove-Item -LiteralPath $target -Recurse -Force
            Write-Output "Removed $target"
        }
        $modsText = Join-Path $modsRoot 'mods.txt'
        if (Test-Path -LiteralPath $modsText) {
            $updated = @(Get-Content -LiteralPath $modsText | Where-Object { $_ -notmatch '^\s*LotFArchipelago\s*:' })
            Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8
        }
    }
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        Remove-Item -LiteralPath $configPath -Force
    }
    Write-UninstallLog ("uninstalled game={0}" -f $gameRoot)
    Write-Output 'Lords of the Fallen Archipelago was uninstalled. UE4SS, saves, logs, backups, and other mods were left unchanged.'
} catch {
    Write-UninstallLog ("uninstall_failed error={0}" -f $_.Exception.Message)
    Write-Error $_.Exception.Message
    exit 1
}
