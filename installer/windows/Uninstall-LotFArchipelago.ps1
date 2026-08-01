[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory)][string]$GamePath)

$ErrorActionPreference = 'Stop'
$gameRoot = (Resolve-Path -LiteralPath $GamePath).Path
$win64 = (Resolve-Path -LiteralPath (Join-Path $gameRoot 'LOTF2\Binaries\Win64')).Path
$modsRoots = @(
    (Join-Path $win64 'ue4ss\Mods'),
    (Join-Path $win64 'Mods')
)
foreach ($modsRoot in $modsRoots) {
    $target = Join-Path $modsRoot 'LotFArchipelago'
    $resolvedModsRoot = [System.IO.Path]::GetFullPath($modsRoot).TrimEnd('\')
    $resolvedTarget = [System.IO.Path]::GetFullPath($target)
    if (-not $resolvedTarget.StartsWith($resolvedModsRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an unexpected path: $resolvedTarget"
    }
    if (Test-Path -LiteralPath $target) {
        if ($PSCmdlet.ShouldProcess($target, 'Remove the LotF Archipelago mod')) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }

    $modsText = Join-Path $modsRoot 'mods.txt'
    if (Test-Path -LiteralPath $modsText) {
        $updated = Get-Content -LiteralPath $modsText | Where-Object { $_ -notmatch '^\s*LotFArchipelago\s*:' }
        Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8
    }
}
Write-Host 'Removed LotF Archipelago. UE4SS and all other mods were left unchanged.'
