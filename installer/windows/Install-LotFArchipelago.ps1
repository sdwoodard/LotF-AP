[CmdletBinding()]
param(
    [string]$GamePath,
    [switch]$AllowMissingUE4SS,
    [switch]$NoGui
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:OutputBox = $null
$script:ProgressBar = $null
$script:ClientVersion = '0.2.4'
$script:ArchipelagoCompatibility = '0.6.7 or newer'
$script:ConfigPath = Join-Path $env:LOCALAPPDATA 'LotFArchipelago\install.json'

$versionFile = Join-Path $PSScriptRoot 'VERSION'
if (Test-Path -LiteralPath $versionFile -PathType Leaf) {
    $script:ClientVersion = (Get-Content -Raw -LiteralPath $versionFile).Trim()
}

function Write-InstallOutput {
    param([string]$Message)
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $Message
    if ($script:OutputBox) {
        $script:OutputBox.AppendText($line + [Environment]::NewLine)
        $script:OutputBox.SelectionStart = $script:OutputBox.TextLength
        $script:OutputBox.ScrollToCaret()
        [System.Windows.Forms.Application]::DoEvents()
    } else {
        Write-Host $line
    }
}

function Set-InstallProgress {
    param([ValidateRange(0, 100)][int]$Value)
    if ($script:ProgressBar) {
        $script:ProgressBar.Value = $Value
        [System.Windows.Forms.Application]::DoEvents()
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

function Resolve-ReleasePayload {
    $payload = Join-Path $PSScriptRoot 'game-mod\LotFArchipelago'
    $main = Join-Path $payload 'Scripts\main.lua'
    if (-not (Test-Path -LiteralPath $main -PathType Leaf)) {
        throw 'The installer must be run from the extracted LotF-Archipelago Windows release folder.'
    }
    $packageVersionFile = Join-Path $PSScriptRoot 'VERSION'
    if (-not (Test-Path -LiteralPath $packageVersionFile -PathType Leaf)) {
        throw 'The extracted release folder has no VERSION file.'
    }
    $packageVersion = (Get-Content -Raw -LiteralPath $packageVersionFile).Trim()
    if ($packageVersion -ne $script:ClientVersion) {
        throw "Installer version $($script:ClientVersion) cannot install package version $packageVersion. Extract matching files from one release."
    }
    return @{ Payload = $payload; Version = $packageVersion }
}

function Save-InstallConfiguration {
    param(
        [string]$ResolvedGamePath,
        [string]$InstalledModPath,
        [hashtable]$Ue4ssCompatibility
    )
    $directory = Split-Path -Parent $script:ConfigPath
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $configuration = [ordered]@{
        schema = 2
        game_path = $ResolvedGamePath
        mod_path = $InstalledModPath
        installed_version = $script:ClientVersion
        tools_path = $PSScriptRoot
        installed_utc = [DateTime]::UtcNow.ToString('o')
    }
    if ($Ue4ssCompatibility -and $Ue4ssCompatibility.SettingsPath) {
        $configuration.ue4ss_settings_path = $Ue4ssCompatibility.SettingsPath
        $configuration.ue4ss_object_array_cache_previous = $Ue4ssCompatibility.Previous
        $configuration.ue4ss_object_array_cache_setting_added = $Ue4ssCompatibility.Added
    }
    $configuration | ConvertTo-Json | Set-Content -LiteralPath $script:ConfigPath -Encoding UTF8
}

function Set-Ue4ssCompatibility {
    param([string]$SettingsPath)
    if (-not $SettingsPath) { return @{} }
    if (-not (Test-Path -LiteralPath $SettingsPath -PathType Leaf)) {
        throw "UE4SS-settings.ini was not found beside UE4SS.dll: $SettingsPath"
    }

    $resolvedSettings = (Resolve-Path -LiteralPath $SettingsPath).Path
    $content = [System.IO.File]::ReadAllText($resolvedSettings)
    $settingPattern = [regex]::new(
        '^(\s*bUseUObjectArrayCache\s*=\s*)(true|false|1|0)(\s*(?:[;#].*)?)$',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor
        [System.Text.RegularExpressions.RegexOptions]::Multiline
    )
    $match = $settingPattern.Match($content)
    $previous = if ($match.Success) { $match.Groups[2].Value } else { $null }
    $added = -not $match.Success

    # Preserve the original value across a reinstall so uninstall can restore
    # what existed before LotF Archipelago first changed this setting.
    if (Test-Path -LiteralPath $script:ConfigPath -PathType Leaf) {
        try {
            $existing = Get-Content -Raw -LiteralPath $script:ConfigPath | ConvertFrom-Json
            $pathProperty = $existing.PSObject.Properties['ue4ss_settings_path']
            $previousProperty = $existing.PSObject.Properties['ue4ss_object_array_cache_previous']
            $addedProperty = $existing.PSObject.Properties['ue4ss_object_array_cache_setting_added']
            if ($pathProperty -and $previousProperty -and
                [string]$pathProperty.Value -eq $resolvedSettings) {
                $previous = $previousProperty.Value
                $added = $addedProperty -and [bool]$addedProperty.Value
            }
        } catch {
            Write-InstallOutput "Warning: could not preserve the previous UE4SS cache value: $($_.Exception.Message)"
        }
    }

    if ($match.Success) {
        $replacement = $match.Groups[1].Value + 'false' + $match.Groups[3].Value
        $content = $content.Substring(0, $match.Index) + $replacement + $content.Substring($match.Index + $match.Length)
    } else {
        if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) { $content += [Environment]::NewLine }
        $content += 'bUseUObjectArrayCache = false' + [Environment]::NewLine
    }
    [System.IO.File]::WriteAllText($resolvedSettings, $content, [System.Text.UTF8Encoding]::new($false))
    Write-InstallOutput 'Configured UE4SS object-array caching off for Lords of the Fallen stability.'
    return @{
        SettingsPath = $resolvedSettings
        Previous = $previous
        Added = $added
    }
}

function Invoke-LotFInstallation {
    param([string]$RequestedGamePath)
    Set-InstallProgress 5
    $package = Resolve-ReleasePayload
    Write-InstallOutput "Using release files beside the installer (version $($package.Version))."
    Set-InstallProgress 25

    if (-not (Test-GameRoot $RequestedGamePath)) {
        throw 'Select the Lords of the Fallen folder containing LOTF2.exe and the LOTF2 subfolder.'
    }
    $resolvedGamePath = (Resolve-Path -LiteralPath $RequestedGamePath).Path
    $win64 = Join-Path $resolvedGamePath 'LOTF2\Binaries\Win64'
    $ue4ssCurrent = Join-Path $win64 'ue4ss\UE4SS.dll'
    $ue4ssLegacy = Join-Path $win64 'UE4SS.dll'
    if (-not (Test-Path -LiteralPath $ue4ssCurrent) -and -not (Test-Path -LiteralPath $ue4ssLegacy)) {
        $message = 'RE-UE4SS was not found in LOTF2\Binaries\Win64. Install the basic UE4SS 3.0.1 package before continuing.'
        if (-not $AllowMissingUE4SS) { throw $message }
        Write-InstallOutput "Warning: $message"
    }
    Write-InstallOutput "Validated game folder: $resolvedGamePath"
    Set-InstallProgress 40

    $ue4ssSettings = if (Test-Path -LiteralPath $ue4ssCurrent) {
        Join-Path (Split-Path -Parent $ue4ssCurrent) 'UE4SS-settings.ini'
    } elseif (Test-Path -LiteralPath $ue4ssLegacy) {
        Join-Path (Split-Path -Parent $ue4ssLegacy) 'UE4SS-settings.ini'
    } else {
        $null
    }
    $ue4ssCompatibility = Set-Ue4ssCompatibility $ue4ssSettings

    $modsDirectory = if (Test-Path -LiteralPath $ue4ssCurrent) { Join-Path $win64 'ue4ss\Mods' } else { Join-Path $win64 'Mods' }
    $target = Join-Path $modsDirectory 'LotFArchipelago'
    New-Item -ItemType Directory -Force -Path $modsDirectory | Out-Null
    if (Test-Path -LiteralPath $target) {
        $backupRoot = Join-Path $env:LOCALAPPDATA 'LotFArchipelago\backups'
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
        Move-Item -LiteralPath $target -Destination $backup
        Write-InstallOutput "Moved the previous mod to: $backup"
    }
    Copy-Item -LiteralPath $package.Payload -Destination $target -Recurse
    Write-InstallOutput "Installed game mod: $target"
    Set-InstallProgress 70

    $modsText = Join-Path $modsDirectory 'mods.txt'
    $lines = if (Test-Path -LiteralPath $modsText) { @(Get-Content -LiteralPath $modsText) } else { @() }
    $found = $false
    $updated = @(foreach ($line in $lines) {
        if ($line -match '^\s*LotFArchipelago\s*:') {
            $found = $true
            'LotFArchipelago : 1'
        } else {
            $line
        }
    })
    if (-not $found) { $updated += 'LotFArchipelago : 1' }
    Set-Content -LiteralPath $modsText -Value $updated -Encoding UTF8
    Write-InstallOutput 'Enabled LotFArchipelago in mods.txt.'
    Set-InstallProgress 85

    Save-InstallConfiguration $resolvedGamePath $target $ue4ssCompatibility
    Write-InstallOutput "Saved the game location for Start and Uninstall: $($script:ConfigPath)"
    Write-InstallOutput 'Installation complete. Install lotf.apworld with Archipelago Launcher before generating or playing.'
    Set-InstallProgress 100
}

if ($NoGui) {
    if (-not $GamePath) {
        $detected = @(Find-SteamGameRoots)
        if ($detected.Count -eq 1) { $GamePath = $detected[0] }
    }
    Invoke-LotFInstallation $GamePath
    exit 0
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = [System.Windows.Forms.Form]::new()
$form.Text = 'Lords of the Fallen Archipelago Installer'
$form.StartPosition = 'CenterScreen'
$form.ClientSize = [System.Drawing.Size]::new(900, 620)
$form.MinimumSize = [System.Drawing.Size]::new(760, 560)
$form.Font = [System.Drawing.Font]::new('Segoe UI', 10)

$versionLabel = [System.Windows.Forms.Label]::new()
$versionLabel.Text = "Client version: $($script:ClientVersion)"
$versionLabel.AutoSize = $true
$versionLabel.Location = [System.Drawing.Point]::new(18, 16)
$form.Controls.Add($versionLabel)

$compatibilityLabel = [System.Windows.Forms.Label]::new()
$compatibilityLabel.Text = "Compatible Archipelago versions: $($script:ArchipelagoCompatibility)"
$compatibilityLabel.AutoSize = $true
$compatibilityLabel.Anchor = 'Top,Right'
$compatibilityLabel.Location = [System.Drawing.Point]::new(535, 16)
$form.Controls.Add($compatibilityLabel)

$separator = [System.Windows.Forms.Label]::new()
$separator.BorderStyle = 'Fixed3D'
$separator.AutoSize = $false
$separator.Location = [System.Drawing.Point]::new(18, 45)
$separator.Size = [System.Drawing.Size]::new(864, 2)
$separator.Anchor = 'Top,Left,Right'
$form.Controls.Add($separator)

function Add-PathRow {
    param([string]$Label, [int]$Top, [string]$InitialValue, [scriptblock]$BrowseAction)
    $caption = [System.Windows.Forms.Label]::new()
    $caption.Text = $Label
    $caption.Location = [System.Drawing.Point]::new(18, $Top + 4)
    $caption.Size = [System.Drawing.Size]::new(190, 24)
    $form.Controls.Add($caption)

    $box = [System.Windows.Forms.TextBox]::new()
    $box.Location = [System.Drawing.Point]::new(210, $Top)
    $box.Size = [System.Drawing.Size]::new(585, 28)
    $box.Anchor = 'Top,Left,Right'
    $box.Text = $InitialValue
    $form.Controls.Add($box)

    $button = [System.Windows.Forms.Button]::new()
    $button.Text = 'Browse...'
    $button.Location = [System.Drawing.Point]::new(805, $Top - 1)
    $button.Size = [System.Drawing.Size]::new(77, 30)
    $button.Anchor = 'Top,Right'
    $browseHandler = { & $BrowseAction $box }.GetNewClosure()
    $button.Add_Click($browseHandler)
    $form.Controls.Add($button)
    return $box
}

$detectedRoots = @(Find-SteamGameRoots)
$defaultGame = if ($GamePath) { $GamePath } elseif ($detectedRoots.Count -eq 1) { $detectedRoots[0] } else { '' }

$gameBox = Add-PathRow 'Lords of the Fallen folder:' 64 $defaultGame {
    param($box)
    $dialog = [System.Windows.Forms.FolderBrowserDialog]::new()
    $dialog.Description = 'Select the folder opened by Steam > Lords of the Fallen > Manage > Browse local files.'
    $dialog.ShowNewFolderButton = $false
    if ($box.Text -and (Test-Path -LiteralPath $box.Text)) { $dialog.SelectedPath = $box.Text }
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $box.Text = $dialog.SelectedPath }
}

$installButton = [System.Windows.Forms.Button]::new()
$installButton.Text = 'Install'
$installButton.Location = [System.Drawing.Point]::new(18, 110)
$installButton.Size = [System.Drawing.Size]::new(864, 38)
$installButton.Anchor = 'Top,Left,Right'
$form.Controls.Add($installButton)

$script:ProgressBar = [System.Windows.Forms.ProgressBar]::new()
$script:ProgressBar.Location = [System.Drawing.Point]::new(18, 160)
$script:ProgressBar.Size = [System.Drawing.Size]::new(864, 24)
$script:ProgressBar.Anchor = 'Top,Left,Right'
$script:ProgressBar.Style = 'Continuous'
$form.Controls.Add($script:ProgressBar)

$outputLabel = [System.Windows.Forms.Label]::new()
$outputLabel.Text = 'Installation output'
$outputLabel.Location = [System.Drawing.Point]::new(18, 200)
$outputLabel.AutoSize = $true
$form.Controls.Add($outputLabel)

$script:OutputBox = [System.Windows.Forms.RichTextBox]::new()
$script:OutputBox.Location = [System.Drawing.Point]::new(18, 227)
$script:OutputBox.Size = [System.Drawing.Size]::new(864, 372)
$script:OutputBox.Anchor = 'Top,Bottom,Left,Right'
$script:OutputBox.ReadOnly = $true
$script:OutputBox.BackColor = [System.Drawing.SystemColors]::Window
$script:OutputBox.DetectUrls = $false
$script:OutputBox.Font = [System.Drawing.Font]::new('Consolas', 9)
$form.Controls.Add($script:OutputBox)

$installButton.Add_Click({
    $installButton.Enabled = $false
    $gameBox.Enabled = $false
    try {
        Invoke-LotFInstallation $gameBox.Text.Trim()
        $installButton.Text = 'Installed'
    } catch {
        Set-InstallProgress 0
        Write-InstallOutput ("ERROR: " + $_.Exception.Message)
        $installButton.Enabled = $true
    } finally {
        $gameBox.Enabled = $true
    }
})

Write-InstallOutput 'Select the game folder, then choose Install.'
[void]$form.ShowDialog()
