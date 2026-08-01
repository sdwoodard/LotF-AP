[CmdletBinding()]
param(
    [string]$GamePath,
    [switch]$AllowMissingUE4SS
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Find-LotFGamePath {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }

    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($env:ProgramFiles) {
        $candidates.Add((Join-Path $env:ProgramFiles 'Steam\steamapps\common\Lords of the Fallen'))
    }
    $steamKeys = @(
        'HKCU:\Software\Valve\Steam',
        'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam'
    )
    foreach ($key in $steamKeys) {
        $installPath = (Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue).SteamPath
        if (-not $installPath) {
            $installPath = (Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue).InstallPath
        }
        if ($installPath) {
            $candidates.Add((Join-Path $installPath 'steamapps\common\Lords of the Fallen'))
            $libraryFile = Join-Path $installPath 'steamapps\libraryfolders.vdf'
            if (Test-Path -LiteralPath $libraryFile) {
                foreach ($match in [regex]::Matches((Get-Content -Raw -LiteralPath $libraryFile), '"path"\s+"([^"]+)"')) {
                    $library = $match.Groups[1].Value -replace '\\\\', '\'
                    $candidates.Add((Join-Path $library 'steamapps\common\Lords of the Fallen'))
                }
            }
        }
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-Path -LiteralPath (Join-Path $candidate 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe')) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw 'Lords of the Fallen was not found. Re-run with -GamePath "<Steam game folder>".'
}

$resolvedGamePath = Find-LotFGamePath $GamePath
$win64 = Join-Path $resolvedGamePath 'LOTF2\Binaries\Win64'
$executable = Join-Path $win64 'LOTF2-Win64-Shipping.exe'
if (-not (Test-Path -LiteralPath $executable)) {
    throw "Not a Lords of the Fallen game folder: $resolvedGamePath"
}

$ue4ssCurrent = Join-Path $win64 'ue4ss\UE4SS.dll'
$ue4ssLegacy = Join-Path $win64 'UE4SS.dll'
if (-not (Test-Path -LiteralPath $ue4ssCurrent) -and -not (Test-Path -LiteralPath $ue4ssLegacy)) {
    $message = 'UE4SS was not found. Install a compatible RE-UE4SS 3.x build in LOTF2\Binaries\Win64 first.'
    if (-not $AllowMissingUE4SS) {
        throw "$message Use -AllowMissingUE4SS to stage this mod before installing UE4SS."
    }
    Write-Warning $message
}

$source = @(
    (Join-Path $PSScriptRoot 'game-mod\LotFArchipelago'),
    (Join-Path $PSScriptRoot '..\game-mod\LotFArchipelago'),
    (Join-Path $PSScriptRoot '..\..\game-mod\LotFArchipelago')
) | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'Scripts\main.lua') } | Select-Object -First 1
if (-not $source -or -not (Test-Path -LiteralPath (Join-Path $source 'Scripts\main.lua'))) {
    throw "The installer payload is incomplete: $source"
}

$modsDirectory = if (Test-Path -LiteralPath $ue4ssCurrent) {
    Join-Path $win64 'ue4ss\Mods'
} else {
    Join-Path $win64 'Mods'
}
$target = Join-Path $modsDirectory 'LotFArchipelago'
New-Item -ItemType Directory -Force -Path $modsDirectory | Out-Null
if (Test-Path -LiteralPath $target) {
    $backupRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago\backups'
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $backup = Join-Path $backupRoot (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
    if (Test-Path -LiteralPath $backup) {
        $backup = Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    }
    Move-Item -LiteralPath $target -Destination $backup
    Write-Host "Previous mod moved to $backup"
}
Copy-Item -LiteralPath $source -Destination $target -Recurse

$modsText = Join-Path $modsDirectory 'mods.txt'
if (Test-Path -LiteralPath $modsText) {
    $lines = @(Get-Content -LiteralPath $modsText)
    $found = $false
    $updated = @(foreach ($line in $lines) {
        if ($line -match '^\s*LotFArchipelago\s*:') {
            $found = $true
            'LotFArchipelago : 1'
        } else {
            $line
        }
    })
    if (-not $found) {
        $updated += 'LotFArchipelago : 1'
    }
    Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8
}

$fileVersion = (Get-Item -LiteralPath $executable).VersionInfo.FileVersion
$fileHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash
Write-Host "Installed LotF Archipelago into $target"
Write-Host "Detected game executable version: $fileVersion"
Write-Host "Detected game executable SHA-256: $fileHash"
Write-Warning 'Use this mod offline only. Do not launch through Easy Anti-Cheat, multiplayer, or invasions.'
Write-Host 'Install lotf.apworld with the Archipelago Launcher, open the Lords of the Fallen Client, then start the game offline.'
