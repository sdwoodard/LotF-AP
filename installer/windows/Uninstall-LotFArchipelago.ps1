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

function Restore-Ue4ssCompatibility($Configuration, [string]$Win64Path) {
    if (-not $Configuration) { return }
    $pathProperty = $Configuration.PSObject.Properties['ue4ss_settings_path']
    $previousProperty = $Configuration.PSObject.Properties['ue4ss_object_array_cache_previous']
    $addedProperty = $Configuration.PSObject.Properties['ue4ss_object_array_cache_setting_added']
    if (-not $pathProperty -or -not $previousProperty) { return }

    $settingsPath = [System.IO.Path]::GetFullPath([string]$pathProperty.Value)
    $resolvedWin64 = [System.IO.Path]::GetFullPath($Win64Path).TrimEnd('\')
    if (-not $settingsPath.StartsWith($resolvedWin64 + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to edit a UE4SS settings path outside the game folder: $settingsPath"
    }
    if (-not (Test-Path -LiteralPath $settingsPath -PathType Leaf)) { return }

    $content = [System.IO.File]::ReadAllText($settingsPath)
    $pattern = [regex]::new(
        '^(\s*bUseUObjectArrayCache\s*=\s*)(true|false|1|0)(\s*(?:[;#].*)?)$',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
        [System.Text.RegularExpressions.RegexOptions]::Multiline
    )
    $match = $pattern.Match($content)
    if (-not $match.Success -or $match.Groups[2].Value -notin @('false', '0')) {
        Write-UninstallLog 'ue4ss_cache_restore_skipped reason=current_value_changed_or_missing'
        return
    }
    if (-not $PSCmdlet.ShouldProcess($settingsPath, 'Restore UE4SS object-array cache setting')) { return }

    $added = $addedProperty -and [bool]$addedProperty.Value
    if ($added) {
        $linePattern = [regex]::new(
            '^\s*bUseUObjectArrayCache\s*=\s*(?:false|0)\s*(?:[;#].*)?\r?\n?',
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
            [System.Text.RegularExpressions.RegexOptions]::Multiline
        )
        $content = $linePattern.Replace($content, '', 1)
    } else {
        $previous = [string]$previousProperty.Value
        $replacement = $match.Groups[1].Value + $previous + $match.Groups[3].Value
        $content = $content.Substring(0, $match.Index) + $replacement + $content.Substring($match.Index + $match.Length)
    }
    [System.IO.File]::WriteAllText($settingsPath, $content, [System.Text.UTF8Encoding]::new($false))
    Write-UninstallLog ("ue4ss_cache_restored path={0}" -f $settingsPath)
    Write-Output 'Restored the UE4SS object-array cache setting that existed before installation.'
}

try {
    $configuration = $null
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        $configuration = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
    }
    if (-not $GamePath) {
        if (-not $configuration) {
            throw 'No saved installation was found. Supply -GamePath only when recovering an installation whose settings file was removed.'
        }
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
    Restore-Ue4ssCompatibility $configuration $win64
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        Remove-Item -LiteralPath $configPath -Force
    }
    Write-UninstallLog ("uninstalled game={0}" -f $gameRoot)
    Write-Output 'Lords of the Fallen Archipelago was uninstalled. UE4SS itself, saves, logs, backups, and other mods were left in place.'
} catch {
    Write-UninstallLog ("uninstall_failed error={0}" -f $_.Exception.Message)
    Write-Error $_.Exception.Message
    exit 1
}
