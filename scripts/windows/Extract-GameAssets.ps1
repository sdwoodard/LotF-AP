[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$GamePath,
    [Parameter(Mandatory)][string]$RetocPath
)

$ErrorActionPreference = 'Stop'
$utoc = Join-Path $GamePath 'LOTF2\Content\Paks\pakchunk0-Windows.utoc'
if (-not (Test-Path -LiteralPath $utoc)) { throw "IoStore index not found: $utoc" }
if (-not (Test-Path -LiteralPath $RetocPath)) { throw "retoc not found: $RetocPath" }

$info = [System.Diagnostics.ProcessStartInfo]::new()
$info.FileName = (Resolve-Path -LiteralPath $RetocPath).Path
$info.Arguments = "list --path `"$utoc`""
$info.UseShellExecute = $false
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$process = [System.Diagnostics.Process]::Start($info)
$listing = $process.StandardOutput.ReadToEnd() + "`n" + $process.StandardError.ReadToEnd()
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "retoc failed with exit code $($process.ExitCode)" }

[regex]::Matches(
    $listing,
    '\.\./\.\./\.\./LOTF2/Content/Blueprints/Data/Equipment/Items/[^\s]+\.uasset'
) | ForEach-Object Value | Sort-Object -Unique
