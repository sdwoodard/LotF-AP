[CmdletBinding()]
param([Parameter(Mandatory)][string]$GamePath)

$ErrorActionPreference = 'Stop'
$gameRoot = (Resolve-Path -LiteralPath $GamePath).Path
$win64 = Join-Path $gameRoot 'LOTF2\Binaries\Win64'
$executable = Join-Path $win64 'LOTF2-Win64-Shipping.exe'
if (-not (Test-Path -LiteralPath $executable)) {
    throw "LOTF2-Win64-Shipping.exe was not found under $gameRoot"
}
$eacProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match 'EasyAntiCheat|start_protected_game'
}
if ($eacProcesses) {
    throw 'Easy Anti-Cheat is running. Close the game and EAC before starting the Archipelago mod.'
}
Write-Warning 'This starts the shipping executable directly for offline mod play. Do not use multiplayer or invasions.'
Start-Process -FilePath $executable -WorkingDirectory $win64 -ArgumentList @('-offline', '-NoEAC')
