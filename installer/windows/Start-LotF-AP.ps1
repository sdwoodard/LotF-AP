[CmdletBinding()]
param([string]$GamePath, [switch]$NoGui, [switch]$DryRun)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$dataRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago'
$configPath = Join-Path $dataRoot 'install.json'
$launcherLog = Join-Path $dataRoot 'logs\lotf-launcher.log'

function Test-GameRoot([string]$Path) {
    return $Path -and (Test-Path -LiteralPath (Join-Path $Path 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'))
}

function Write-LauncherLog([string]$Message) {
    $directory = Split-Path -Parent $launcherLog
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    Add-Content -LiteralPath $launcherLog -Value ("{0} {1}" -f [DateTime]::UtcNow.ToString('o'), $Message) -Encoding UTF8
}

try {
    if (-not $GamePath) {
        if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
            throw 'No saved installation was found. Run Install-LotFArchipelago.cmd first.'
        }
        $configuration = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
        $GamePath = [string]$configuration.game_path
    }
    if (-not (Test-GameRoot $GamePath)) {
        throw "The saved Lords of the Fallen folder is no longer valid: $GamePath. Run the installer again to select its current location."
    }
    $gameRoot = (Resolve-Path -LiteralPath $GamePath).Path
    $win64 = Join-Path $gameRoot 'LOTF2\Binaries\Win64'
    $executable = Join-Path $win64 'LOTF2-Win64-Shipping.exe'

    if (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'EasyAntiCheat|start_protected_game' }) {
        throw 'Easy Anti-Cheat is running. Close it before starting the Archipelago session.'
    }
    if (-not (Get-Process -Name steam -ErrorAction SilentlyContinue)) {
        throw 'Steam is not running. Start Steam with the account that owns the full game.'
    }
    foreach ($appIdFile in @((Join-Path $gameRoot 'steam_appid.txt'), (Join-Path $win64 'steam_appid.txt'))) {
        if (Test-Path -LiteralPath $appIdFile) {
            throw "Remove the unsupported file before launching: $appIdFile"
        }
    }

    # Keep the owned full-game identity while disabling the anti-cheat and the
    # Redpoint EOS multiplayer subsystem for this child process.
    $env:SteamAppId = '1501750'
    $env:SteamGameId = '1501750'
    $env:EOS_DISABLE_OVERLAY = '1'
    $arguments = @('-NoEAC', '-Offline', '-NoRedpointEOS', '-NoOnlineSubsystemRedpointEOS')
    Write-LauncherLog ("launch_requested game={0} executable={1} arguments={2}" -f $gameRoot, $executable, ($arguments -join ' '))

    if ($DryRun) {
        Write-Output ('"{0}" {1}' -f $executable, ($arguments -join ' '))
        exit 0
    }
    $process = Start-Process -FilePath $executable -WorkingDirectory $win64 -ArgumentList $arguments -PassThru
    Write-LauncherLog ("launch_started pid={0} steam_app_id=1501750 offline_flags=enabled" -f $process.Id)
} catch {
    Write-LauncherLog ("launch_failed error={0}" -f $_.Exception.Message)
    Write-Error $_.Exception.Message
    exit 1
}
