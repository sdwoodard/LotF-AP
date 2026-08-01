[CmdletBinding()]
param([string]$GamePath, [switch]$NoGui)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$interactive = -not $NoGui

function Show-Message {
    param([string]$Text, [string]$Title = 'Lords of the Fallen Archipelago', [string]$Icon = 'Information')
    if ($interactive) {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Text, $Title, [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::$Icon
        ) | Out-Null
    } else { Write-Host $Text }
}

function Test-GameRoot([string]$Path) {
    return $Path -and (Test-Path -LiteralPath (Join-Path $Path 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'))
}

function Find-GameRoot {
    if (Test-GameRoot $GamePath) { return (Resolve-Path -LiteralPath $GamePath).Path }
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($key in @('HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam')) {
        $properties = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if (-not $properties) { continue }
        $steamProperty = $properties.PSObject.Properties['SteamPath']
        $installProperty = $properties.PSObject.Properties['InstallPath']
        $steamPath = if ($steamProperty) { $steamProperty.Value } elseif ($installProperty) { $installProperty.Value } else { $null }
        if (-not $steamPath) { continue }
        $candidates.Add((Join-Path $steamPath 'steamapps\common\Lords of the Fallen'))
        $libraries = Join-Path $steamPath 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $libraries) {
            foreach ($match in [regex]::Matches((Get-Content -Raw -LiteralPath $libraries), '"path"\s+"([^"]+)"')) {
                $library = $match.Groups[1].Value -replace '\\\\', '\'
                $candidates.Add((Join-Path $library 'steamapps\common\Lords of the Fallen'))
            }
        }
    }
    $matches = @($candidates | Select-Object -Unique | Where-Object { Test-GameRoot $_ })
    if ($matches.Count -eq 1 -and -not $interactive) { return (Resolve-Path -LiteralPath $matches[0]).Path }
    if (-not $interactive) { throw 'Supply -GamePath with the Steam game folder.' }

    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
    $dialog.Description = 'Select the Lords of the Fallen folder opened by Steam > Manage > Browse local files.'
    $dialog.ShowNewFolderButton = $false
    if ($matches.Count -ge 1) { $dialog.SelectedPath = $matches[0] }
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Game-folder selection was cancelled.' }
    if (-not (Test-GameRoot $dialog.SelectedPath)) {
        throw 'Select the folder containing LOTF2.exe and the LOTF2 subfolder.'
    }
    return (Resolve-Path -LiteralPath $dialog.SelectedPath).Path
}

try {
    $gameRoot = Find-GameRoot
    $win64 = Join-Path $gameRoot 'LOTF2\Binaries\Win64'
    $executable = Join-Path $win64 'LOTF2-Win64-Shipping.exe'
    if (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'EasyAntiCheat|start_protected_game' }) {
        throw 'Easy Anti-Cheat is running. Close the game and anti-cheat before starting the Archipelago session.'
    }
    if (-not (Get-Process -Name steam -ErrorAction SilentlyContinue)) {
        throw 'Steam is not running. Start Steam with the account that owns the full Lords of the Fallen game, then try again.'
    }
    $appIdFiles = @(
        (Join-Path $gameRoot 'steam_appid.txt'),
        (Join-Path $win64 'steam_appid.txt')
    )
    foreach ($appIdFile in $appIdFiles) {
        if (Test-Path -LiteralPath $appIdFile) {
            throw "Remove the unsupported file $appIdFile before launching. This project sets Steam identity only for the child process."
        }
    }

    if ($interactive) {
        Add-Type -AssemblyName System.Windows.Forms
        $answer = [System.Windows.Forms.MessageBox]::Show(
            "Steam must be signed into an account that owns the full game (AppID 1501750).`n`n" +
            "Set Steam to Offline Mode or disable all in-game online features. Never use matchmaking, co-op, or invasions with UE4SS loaded.`n`n" +
            "Start the game now?",
            'Start Lords of the Fallen Archipelago',
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
        if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { exit 0 }
    }

    # Directly launching the shipping executable is required for UE4SS/no-EAC.
    # Supplying the owned game's Steam identity prevents the executable from
    # inheriting the Free Friend's Pass entitlement (AppID 3664720).
    $env:SteamAppId = '1501750'
    $env:SteamGameId = '1501750'
    Start-Process -FilePath $executable -WorkingDirectory $win64 -ArgumentList @('-NoEAC')
} catch {
    Show-Message $_.Exception.Message 'Game did not start' 'Error'
    exit 1
}
