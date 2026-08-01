[CmdletBinding()]
param(
    [string]$GamePath,
    [string]$ReleaseZip,
    [switch]$AllowMissingUE4SS,
    [switch]$NoGui
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:Interactive = -not $NoGui
$script:TemporaryRoot = $null
$script:ReleaseRoot = $null

function Show-Message {
    param([string]$Text, [string]$Title = 'Lords of the Fallen Archipelago', [string]$Icon = 'Information')
    if ($script:Interactive) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Text,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::$Icon
        ) | Out-Null
    } else {
        Write-Host $Text
    }
}

function Test-GameRoot {
    param([string]$Path)
    return $Path -and (Test-Path -LiteralPath (Join-Path $Path 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'))
}

function Find-SteamGameRoots {
    $roots = [System.Collections.Generic.List[string]]::new()
    foreach ($key in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
        $properties = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if (-not $properties) { continue }
        $steamProperty = $properties.PSObject.Properties['SteamPath']
        $installProperty = $properties.PSObject.Properties['InstallPath']
        $steamPath = if ($steamProperty) { $steamProperty.Value } elseif ($installProperty) { $installProperty.Value } else { $null }
        if (-not $steamPath) { continue }
        $roots.Add((Join-Path $steamPath 'steamapps\common\Lords of the Fallen'))
        $libraries = Join-Path $steamPath 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $libraries) {
            foreach ($match in [regex]::Matches((Get-Content -Raw -LiteralPath $libraries), '"path"\s+"([^"]+)"')) {
                $library = $match.Groups[1].Value -replace '\\\\', '\'
                $roots.Add((Join-Path $library 'steamapps\common\Lords of the Fallen'))
            }
        }
    }
    return @($roots | Select-Object -Unique | Where-Object { Test-GameRoot $_ })
}

function Select-GameRoot {
    param([string]$InitialPath)
    if (-not $script:Interactive) {
        if (-not (Test-GameRoot $InitialPath)) { throw 'Supply -GamePath with the Steam game folder.' }
        return (Resolve-Path -LiteralPath $InitialPath).Path
    }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
    $dialog.Description = 'Select the Lords of the Fallen folder opened by Steam > Manage > Browse local files.'
    $dialog.ShowNewFolderButton = $false
    if ($InitialPath -and (Test-Path -LiteralPath $InitialPath)) { $dialog.SelectedPath = $InitialPath }
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Game-folder selection was cancelled.' }
    if (-not (Test-GameRoot $dialog.SelectedPath)) {
        throw 'That folder is not the Lords of the Fallen root. Select the folder containing LOTF2.exe and the LOTF2 subfolder.'
    }
    return (Resolve-Path -LiteralPath $dialog.SelectedPath).Path
}

function Find-Payload {
    param([string]$Root)
    $candidates = @(
        (Join-Path $Root 'game-mod\LotFArchipelago'),
        (Join-Path $Root '..\game-mod\LotFArchipelago'),
        (Join-Path $Root '..\..\game-mod\LotFArchipelago')
    )
    $direct = $candidates | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'Scripts\main.lua') } | Select-Object -First 1
    if ($direct) { return (Resolve-Path -LiteralPath $direct).Path }
    return $null
}

function Select-ReleaseZip {
    param([string]$RequestedPath)
    if ($RequestedPath) {
        if (-not (Test-Path -LiteralPath $RequestedPath -PathType Leaf)) { throw "Release package not found: $RequestedPath" }
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }
    if (-not $script:Interactive) { throw 'Supply -ReleaseZip with LotF-Archipelago-x.y.z-win64.zip.' }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.OpenFileDialog]::new()
    $dialog.Title = 'Select the downloaded Lords of the Fallen Archipelago Windows package'
    $dialog.Filter = 'LotF Archipelago Windows package (LotF-Archipelago-*-win64.zip)|LotF-Archipelago-*-win64.zip|ZIP archives (*.zip)|*.zip'
    $dialog.CheckFileExists = $true
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Release-package selection was cancelled.' }
    return $dialog.FileName
}

function Expand-ReleasePayload {
    param([string]$Archive)
    $base = Join-Path ([System.IO.Path]::GetTempPath()) 'LotFArchipelagoInstaller'
    New-Item -ItemType Directory -Force -Path $base | Out-Null
    $script:TemporaryRoot = Join-Path $base ([guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $script:TemporaryRoot | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $script:TemporaryRoot
    $main = Get-ChildItem -LiteralPath $script:TemporaryRoot -Filter main.lua -File -Recurse |
        Where-Object { $_.FullName -match '[\\/]game-mod[\\/]LotFArchipelago[\\/]Scripts[\\/]main\.lua$' } |
        Select-Object -First 1
    if (-not $main) { throw 'The selected ZIP does not contain game-mod\LotFArchipelago\Scripts\main.lua.' }
    $payload = Split-Path -Parent (Split-Path -Parent $main.FullName)
    $script:ReleaseRoot = Split-Path -Parent (Split-Path -Parent $payload)
    return $payload
}

function Export-CompanionFiles {
    if (-not $script:TemporaryRoot -or -not $script:ReleaseRoot) { return $null }
    $relativeFiles = @(
        'lotf.apworld',
        'Lords of the Fallen.yaml',
        'README.md',
        'CHANGELOG.md',
        'VERSION',
        'Start-LotF-AP.cmd',
        'Start-LotF-AP.ps1',
        'Uninstall-LotFArchipelago.cmd',
        'Uninstall-LotFArchipelago.ps1',
        'New-LotFDiagnosticBundle.cmd',
        'New-LotFDiagnosticBundle.ps1'
    )
    foreach ($relative in $relativeFiles) {
        $sourceFile = Join-Path $script:ReleaseRoot $relative
        if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
            throw "The selected release is missing companion file: $relative"
        }
        Copy-Item -LiteralPath $sourceFile -Destination (Join-Path $PSScriptRoot $relative) -Force
    }
    return $PSScriptRoot
}

try {
    $source = Find-Payload $PSScriptRoot
    if (-not $source) {
        $archive = Select-ReleaseZip $ReleaseZip
        $source = Expand-ReleasePayload $archive
    }

    $detected = @(Find-SteamGameRoots)
    $initial = if ($GamePath) { $GamePath } elseif ($detected.Count -eq 1) { $detected[0] } else { '' }
    $resolvedGamePath = Select-GameRoot $initial
    $win64 = Join-Path $resolvedGamePath 'LOTF2\Binaries\Win64'
    $executable = Join-Path $win64 'LOTF2-Win64-Shipping.exe'

    $ue4ssCurrent = Join-Path $win64 'ue4ss\UE4SS.dll'
    $ue4ssLegacy = Join-Path $win64 'UE4SS.dll'
    if (-not (Test-Path -LiteralPath $ue4ssCurrent) -and -not (Test-Path -LiteralPath $ue4ssLegacy)) {
        $message = @'
RE-UE4SS was not found in LOTF2\Binaries\Win64.

Download the basic UE4SS 3.0.1 package from the official RE-UE4SS GitHub release, extract its files directly into that Win64 folder, launch the game once with anti-cheat disabled, and then run this installer again. See README.md for the exact link and file layout.
'@
        if (-not $AllowMissingUE4SS) { throw $message }
        Show-Message $message 'RE-UE4SS not detected' 'Warning'
    }

    $modsDirectory = if (Test-Path -LiteralPath $ue4ssCurrent) { Join-Path $win64 'ue4ss\Mods' } else { Join-Path $win64 'Mods' }
    $target = Join-Path $modsDirectory 'LotFArchipelago'
    New-Item -ItemType Directory -Force -Path $modsDirectory | Out-Null
    if (Test-Path -LiteralPath $target) {
        $backupRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago\backups'
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
        Move-Item -LiteralPath $target -Destination $backup
    }
    Copy-Item -LiteralPath $source -Destination $target -Recurse

    $modsText = Join-Path $modsDirectory 'mods.txt'
    $lines = if (Test-Path -LiteralPath $modsText) { @(Get-Content -LiteralPath $modsText) } else { @() }
    $found = $false
    $updated = @(foreach ($line in $lines) {
        if ($line -match '^\s*LotFArchipelago\s*:') { $found = $true; 'LotFArchipelago : 1' } else { $line }
    })
    if (-not $found) { $updated += 'LotFArchipelago : 1' }
    Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8

    $versionFile = Join-Path $target 'VERSION'
    $installedVersion = if (Test-Path -LiteralPath $versionFile) { (Get-Content -Raw -LiteralPath $versionFile).Trim() } else { 'unknown' }
    $companionDirectory = Export-CompanionFiles
    $companionText = if ($companionDirectory) {
        "`nPlayer tools: $companionDirectory`n`nInstall lotf.apworld from that folder, then use Start-LotF-AP.cmd for every modded session."
    } else {
        "`n`nInstall lotf.apworld from this extracted release, then use Start-LotF-AP.cmd for every modded session."
    }
    Show-Message (
        "Installed Lords of the Fallen Archipelago $installedVersion.`n`n" +
        "Game: $resolvedGamePath`nMod: $target" + $companionText
    )
} catch {
    Show-Message $_.Exception.Message 'Installation did not complete' 'Error'
    exit 1
} finally {
    if ($script:TemporaryRoot -and (Test-Path -LiteralPath $script:TemporaryRoot)) {
        $base = [System.IO.Path]::GetFullPath((Join-Path ([System.IO.Path]::GetTempPath()) 'LotFArchipelagoInstaller')).TrimEnd('\')
        $resolvedTemporary = [System.IO.Path]::GetFullPath($script:TemporaryRoot)
        if ($resolvedTemporary.StartsWith($base + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedTemporary -Recurse -Force
        }
    }
}
