[CmdletBinding(SupportsShouldProcess)]
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

function Select-GameRoot {
    if (Test-GameRoot $GamePath) { return (Resolve-Path -LiteralPath $GamePath).Path }
    if (-not $interactive) { throw 'Supply -GamePath with the Steam game folder.' }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
    $dialog.Description = 'Select the Lords of the Fallen folder opened by Steam > Manage > Browse local files.'
    $dialog.ShowNewFolderButton = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw 'Game-folder selection was cancelled.' }
    if (-not (Test-GameRoot $dialog.SelectedPath)) { throw 'Select the folder containing LOTF2.exe and the LOTF2 subfolder.' }
    return (Resolve-Path -LiteralPath $dialog.SelectedPath).Path
}

try {
    $gameRoot = Select-GameRoot
    if ($interactive) {
        Add-Type -AssemblyName System.Windows.Forms
        $answer = [System.Windows.Forms.MessageBox]::Show(
            "Remove only the LotFArchipelago UE4SS mod from:`n$gameRoot`n`nUE4SS, other mods, saves, logs, and backups will be left unchanged.",
            'Uninstall Lords of the Fallen Archipelago',
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question
        )
        if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { exit 0 }
    }
    $win64 = (Resolve-Path -LiteralPath (Join-Path $gameRoot 'LOTF2\Binaries\Win64')).Path
    $modsRoots = @(
        (Join-Path $win64 'ue4ss\Mods'),
        (Join-Path $win64 'Mods')
    )
    foreach ($modsRoot in $modsRoots) {
        $target = Join-Path $modsRoot 'LotFArchipelago'
        $resolvedRoot = [System.IO.Path]::GetFullPath($modsRoot).TrimEnd('\')
        $resolvedTarget = [System.IO.Path]::GetFullPath($target)
        if (-not $resolvedTarget.StartsWith($resolvedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove an unexpected path: $resolvedTarget"
        }
        if ((Test-Path -LiteralPath $target) -and $PSCmdlet.ShouldProcess($target, 'Remove LotFArchipelago')) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
        $modsText = Join-Path $modsRoot 'mods.txt'
        if (Test-Path -LiteralPath $modsText) {
            $updated = @(Get-Content -LiteralPath $modsText | Where-Object { $_ -notmatch '^\s*LotFArchipelago\s*:' })
            Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8
        }
    }
    Show-Message 'Removed the LotFArchipelago UE4SS mod. UE4SS, other mods, saves, logs, and backups were left unchanged.'
} catch {
    Show-Message $_.Exception.Message 'Uninstall did not complete' 'Error'
    exit 1
}
