[CmdletBinding()]
param(
    [string]$GamePath,
    [string]$RetocPath,
    [string]$PythonPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$manifest = Get-Content -Raw -LiteralPath (Join-Path $root 'worlds\lotf\archipelago.json') | ConvertFrom-Json
$version = (Get-Content -Raw -LiteralPath (Join-Path $root 'VERSION')).Trim()
if ($manifest.world_version -ne $version) {
    throw "VERSION ($version) and archipelago.json ($($manifest.world_version)) differ."
}
if ($manifest.compatible_version -ne 7 -or $manifest.version -ne 7) {
    throw 'archipelago.json must declare APWorld container compatible_version/version 7.'
}
$luaBridge = Get-Content -Raw -LiteralPath (Join-Path $root 'game-mod\LotFArchipelago\Scripts\bridge.lua')
$luaVersion = [regex]::Match($luaBridge, 'version\s*=\s*"([^"]+)"').Groups[1].Value
if ($luaVersion -ne $version) {
    throw "VERSION ($version) and Lua bridge version ($luaVersion) differ."
}
$luaProtocol = [int][regex]::Match($luaBridge, 'protocol_version\s*=\s*(\d+)').Groups[1].Value
$pythonBridge = Get-Content -Raw -LiteralPath (Join-Path $root 'worlds\lotf\client\bridge.py')
$pythonProtocol = [int][regex]::Match($pythonBridge, 'PROTOCOL_VERSION\s*=\s*(\d+)').Groups[1].Value
if ($luaProtocol -ne $pythonProtocol) {
    throw "Python bridge protocol ($pythonProtocol) and Lua bridge protocol ($luaProtocol) differ."
}
if ($luaBridge.IndexOf('B21D92B8406214F0AEAF6B9B239BB661', [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
    throw 'Lua bridge is missing the explicit tutorial Throwing Stone pickup guard.'
}
if ($luaBridge.IndexOf('/Script/LOTF2.Pickup:OnTakePickupEndDelegate', [System.StringComparison]::Ordinal) -lt 0) {
    throw 'Lua bridge is missing the pickup-completion correlation hook.'
}
foreach ($pickupRuntimePath in @('Pickup:PickupSetupFinished', 'Pickup:Show', 'Pickup:TryTakePickup', 'LoadAsset(load_path)')) {
    if ($luaBridge.IndexOf($pickupRuntimePath, [System.StringComparison]::Ordinal) -lt 0) {
        throw "Lua bridge is missing required pickup runtime path: $pickupRuntimePath"
    }
}
foreach ($unsafePickupPath in @('subsystem.RegisteredPickups', 'pickups:ForEach', 'NotifyOnNewObject(', 'FindAllOf("Pickup")', 'pickup_scan', 'asset_classes', 'archipelago_icon = texture')) {
    if ($luaBridge.IndexOf($unsafePickupPath, [System.StringComparison]::Ordinal) -ge 0) {
        throw "Lua bridge retains unsafe pickup/object-lifetime path: $unsafePickupPath"
    }
}
$worldSource = Get-Content -Raw -LiteralPath (Join-Path $root 'worlds\lotf\world.py')
$slotVersion = [regex]::Match($worldSource, '"world_version":\s*"([^"]+)"').Groups[1].Value
if ($slotVersion -ne $version) {
    throw "VERSION ($version) and slot-data version ($slotVersion) differ."
}

$required = @(
    'worlds\lotf\__init__.py',
    'worlds\lotf\world.py',
    'worlds\lotf\client\client.py',
    'worlds\lotf\assets\lotf-icon.png',
    'game-mod\LotFArchipelago\Scripts\main.lua',
    'game-mod\LotFArchipelago\Scripts\bridge.lua',
    'game-mod\LotFArchipelago\Assets\archipelago.png',
    '.github\assets\lotf-icon.png',
    '.github\assets\social-preview.jpg',
    'installer\windows\Install-LotFArchipelago.ps1',
    'installer\windows\Install-LotFArchipelago.cmd',
    'worlds\lotf\preplaced_pickups.py'
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $relative))) {
        throw "Required file is missing: $relative"
    }
}

$powershellFiles = Get-ChildItem -LiteralPath $root -Filter '*.ps1' -Recurse -File
foreach ($file in $powershellFiles) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors)
    if ($errors.Count) {
        throw "PowerShell parse error in $($file.FullName): $($errors[0].Message)"
    }
}

$installerSource = Get-Content -Raw -LiteralPath (Join-Path $root 'installer\windows\Install-LotFArchipelago.ps1')
foreach ($control in @('System.Windows.Forms.Form', 'System.Windows.Forms.ProgressBar', 'System.Windows.Forms.RichTextBox')) {
    if ($installerSource.IndexOf($control, [System.StringComparison]::Ordinal) -lt 0) {
        throw "Windows installer is missing required GUI control: $control"
    }
}
if ($installerSource.IndexOf("ReadOnly = `$true", [System.StringComparison]::Ordinal) -lt 0 -or
    $installerSource.IndexOf('install.json', [System.StringComparison]::Ordinal) -lt 0) {
    throw 'Windows installer must provide read-only output and save install.json.'
}
if ($installerSource.IndexOf('ReleaseZip', [System.StringComparison]::Ordinal) -ge 0 -or
    $installerSource.IndexOf('game-mod\LotFArchipelago', [System.StringComparison]::Ordinal) -lt 0) {
    throw 'Windows installer must use the extracted release files beside itself without a package picker.'
}
$uninstallerSource = Get-Content -Raw -LiteralPath (Join-Path $root 'installer\windows\Uninstall-LotFArchipelago.ps1')
foreach ($cacheContract in @('bUseUObjectArrayCache', "'false'", 'ue4ss_object_array_cache_previous')) {
    if ($installerSource.IndexOf($cacheContract, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Windows installer is missing the UE4SS cache compatibility contract: $cacheContract"
    }
}
foreach ($restoreContract in @('Restore-Ue4ssCompatibility', 'ue4ss_object_array_cache_previous')) {
    if ($uninstallerSource.IndexOf($restoreContract, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Windows uninstaller is missing the UE4SS cache restoration contract: $restoreContract"
    }
}
$launcherSource = Get-Content -Raw -LiteralPath (Join-Path $root 'installer\windows\Start-LotF-AP.ps1')
foreach ($offlineSetting in @('-NoEAC', '-Offline', '-NoRedpointEOS', '-NoOnlineSubsystemRedpointEOS', "SteamAppId = '1501750'")) {
    if ($launcherSource.IndexOf($offlineSetting, [System.StringComparison]::Ordinal) -lt 0) {
        throw "Windows launcher is missing offline/full-game setting: $offlineSetting"
    }
}
foreach ($gameOfflineSetting in @('SetOnlineModeEnabled(false)', 'SetCrossplayEnabled(false)', 'SetAllowInvasionsEnabled(false)')) {
    if ($luaBridge.IndexOf($gameOfflineSetting, [System.StringComparison]::Ordinal) -lt 0) {
        throw "Lua bridge is missing game offline safeguard: $gameOfflineSetting"
    }
}
if ($launcherSource.IndexOf('ShowDialog', [System.StringComparison]::Ordinal) -ge 0 -or
    $launcherSource.IndexOf('MessageBox', [System.StringComparison]::Ordinal) -ge 0) {
    throw 'Windows launcher must start without a picker or confirmation dialog.'
}
$buildSource = Get-Content -Raw -LiteralPath (Join-Path $root 'scripts\windows\Build-Release.ps1')
if ($buildSource.IndexOf('Windows-Installer', [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
    throw 'The separate Windows installer archive must not be built.'
}
if ($buildSource -match "Copy-Item[^`r`n]+CHANGELOG\.md" -or
    $buildSource -match "Copy-Item[^`r`n]+docs\\") {
    throw 'Player release archives must not contain repository-only changelog or developer documentation.'
}
if ($buildSource.IndexOf('Assets\README.txt', [System.StringComparison]::Ordinal) -lt 0) {
    throw 'The release builder must remove the runtime-unnecessary asset provenance note.'
}

if ($GamePath) {
    $utoc = Join-Path $GamePath 'LOTF2\Content\Paks\pakchunk0-Windows.utoc'
    $globalUtoc = Join-Path $GamePath 'LOTF2\Content\Paks\global.utoc'
    $executable = Join-Path $GamePath 'LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe'
    if (-not (Test-Path -LiteralPath $utoc) -or -not (Test-Path -LiteralPath $globalUtoc) -or -not (Test-Path -LiteralPath $executable)) {
        throw "The supplied game path is incomplete: $GamePath"
    }
    $executableItem = Get-Item -LiteralPath $executable
    $executableHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash
    $buildDocumentation = Get-Content -Raw -LiteralPath (Join-Path $root 'docs\GAME_BUILD.md')
    if ($buildDocumentation.IndexOf($executableHash, [System.StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        $buildDocumentation.IndexOf([string]$executableItem.Length, [System.StringComparison]::Ordinal) -lt 0) {
        throw "The supplied executable hash/size is not recorded in docs\GAME_BUILD.md. Audit the game update before changing the supported build."
    }
    Write-Host "Validated documented game executable: SHA-256=$executableHash size=$($executableItem.Length)"
    $executableText = [System.Text.Encoding]::ASCII.GetString(
        [System.IO.File]::ReadAllBytes($executable)
    )
    $requiredReflectionNames = @(
        '/Script/LOTF2',
        'AAnathemaItemContainer::AddItemToInventory',
        'GetInventoryComponent',
        'DEBUG_SeverAddInventoryItem',
        'GetInventoryItemFromClass',
        'GetInventoryItemFromItemData',
        'GetFullStock',
        'GetUsableStock',
        'GetItemName',
        'GetItemDescription',
        'GetItemIcon',
        'ImportFileAsTexture2D',
        'SaveGameSync',
        'SaveGameAsync',
        'OnCreditScreenEndedCallback',
        'TryTakePickup',
        'PickupSetupFinished',
        'OnTakePickupEndDelegate',
        'GetStringId',
        'PrePlacedRandomLootMap'
    )
    $missingReflectionNames = @($requiredReflectionNames | Where-Object {
        $executableText.IndexOf($_, [System.StringComparison]::Ordinal) -lt 0
    })
    if ($missingReflectionNames.Count) {
        throw "Game executable is missing reflected bridge names: $($missingReflectionNames -join ', ')"
    }
    Write-Host "Validated $($requiredReflectionNames.Count) reflected bridge names in the game executable."

    $dataText = Get-Content -Raw -LiteralPath (Join-Path $root 'worlds\lotf\data.py')
    $assetNames = [regex]::Matches($dataText, 'ITM_[A-Za-z0-9_]+') | ForEach-Object Value | Sort-Object -Unique
    $utocBytes = [System.IO.File]::ReadAllBytes($utoc)
    $utocText = [System.Text.Encoding]::ASCII.GetString($utocBytes)
    $missing = @($assetNames | Where-Object { $utocText.IndexOf($_, [System.StringComparison]::Ordinal) -lt 0 })
    if ($missing.Count) {
        throw "Game build is missing $($missing.Count) mapped assets: $($missing -join ', ')"
    }
    Write-Host "Validated $($assetNames.Count) mapped asset names against the installed IoStore index."

    if (-not $RetocPath) {
        $localRetoc = Join-Path (Split-Path -Parent $root) '.tools\retoc\retoc.exe'
        if (Test-Path -LiteralPath $localRetoc) {
            $RetocPath = $localRetoc
        }
    }
    if ($RetocPath) {
        $retoc = (Resolve-Path -LiteralPath $RetocPath).Path
        $manifestRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('LotF-retoc-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $manifestRoot | Out-Null
        try {
            $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
            $startInfo.FileName = $retoc
            $startInfo.Arguments = "manifest `"$utoc`""
            $startInfo.WorkingDirectory = $manifestRoot
            $startInfo.UseShellExecute = $false
            $startInfo.RedirectStandardOutput = $true
            $startInfo.RedirectStandardError = $true
            $process = [System.Diagnostics.Process]::Start($startInfo)
            $manifestLog = $process.StandardOutput.ReadToEnd() + "`n" + $process.StandardError.ReadToEnd()
            $process.WaitForExit()
            $manifestPath = Join-Path $manifestRoot 'pakstore.json'
            if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $manifestPath)) {
                throw "retoc manifest failed with exit code $($process.ExitCode): $manifestLog"
            }
            $packageManifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
            $packageNames = @($packageManifest.oplog.entries | ForEach-Object {
                $_.packagestoreentry.packagename
            })
            $relativeAssets = [regex]::Matches($dataText, 'item_asset\("([^"]+)"\)') |
                ForEach-Object { $_.Groups[1].Value } |
                Sort-Object -Unique
            $expectedPaths = @($relativeAssets | ForEach-Object {
                "/Game/Blueprints/Data/Equipment/Items/$_"
            })
            $expectedPaths += @(
                '/Game/Blueprints/Data/Equipment/Items/Usables/VigorStones/ITM_CON_VigorStone_01',
                '/Game/Core/Characters/Player/AnathemaPlayerCharacter_BP',
                '/Game/Blueprints/Data/LootTables/DA_PrePlacedRandomLootMap'
            )
            $missingPaths = @($expectedPaths | Sort-Object -Unique | Where-Object { $_ -notin $packageNames })
            if ($missingPaths.Count) {
                throw "Game build is missing $($missingPaths.Count) exact cooked paths: $($missingPaths -join ', ')"
            }
            Write-Host "Validated $($expectedPaths.Count) exact cooked paths with retoc."
        } finally {
            if (Test-Path -LiteralPath $manifestRoot) {
                Remove-Item -LiteralPath $manifestRoot -Recurse -Force
            }
        }

        $scriptInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $scriptInfo.FileName = $retoc
        $scriptInfo.Arguments = "print-script-objects `"$globalUtoc`""
        $scriptInfo.UseShellExecute = $false
        $scriptInfo.RedirectStandardOutput = $true
        $scriptInfo.RedirectStandardError = $true
        $scriptProcess = [System.Diagnostics.Process]::Start($scriptInfo)
        $scriptObjects = $scriptProcess.StandardOutput.ReadToEnd() + "`n" + $scriptProcess.StandardError.ReadToEnd()
        $scriptProcess.WaitForExit()
        if ($scriptProcess.ExitCode -ne 0) {
            throw "retoc script-object validation failed with exit code $($scriptProcess.ExitCode)."
        }
        $requiredCompletionObjects = @(
            'HexFinishGameManager:',
            'OnCreditScreenEndedCallback:',
            'InventoryComponent:',
            'GetInventoryItemFromClass:',
            'InventoryItem:',
            'GetFullStock:',
            'LOTF2SaveGameManager:',
            'SaveGameSync:',
            'ItemData:',
            'GetItemIcon:',
            'ImportFileAsTexture2D:'
        )
        $missingCompletionObjects = @($requiredCompletionObjects | Where-Object {
            $scriptObjects.IndexOf($_, [System.StringComparison]::Ordinal) -lt 0
        })
        if ($missingCompletionObjects.Count) {
            throw "Game build is missing ending-completion objects: $($missingCompletionObjects -join ', ')"
        }
        Write-Host 'Validated the reflected credits-completion hook with retoc.'
    } else {
        Write-Warning 'retoc was not supplied; exact cooked-path validation was skipped.'
    }
}

$pythonExecutable = $null
if ($PythonPath) {
    $pythonExecutable = (Resolve-Path -LiteralPath $PythonPath).Path
} else {
    $localPython = Join-Path (Split-Path -Parent $root) '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $localPython) {
        $pythonExecutable = $localPython
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python -and $python.Source -notmatch 'WindowsApps') {
            $pythonExecutable = $python.Source
        }
    }
}
if ($pythonExecutable) {
    & $pythonExecutable -m compileall -q (Join-Path $root 'worlds\lotf')
    if ($LASTEXITCODE -ne 0) { throw 'Python compilation failed.' }
    & $pythonExecutable (Join-Path $root 'scripts\common\Validate-PngAlpha.py') `
        (Join-Path $root 'game-mod\LotFArchipelago\Assets\archipelago.png') `
        (Join-Path $root 'worlds\lotf\assets\lotf-icon.png') `
        (Join-Path $root '.github\assets\lotf-icon.png')
    if ($LASTEXITCODE -ne 0) { throw 'PNG transparency validation failed.' }
    & $pythonExecutable (Join-Path $root 'scripts\common\Validate-SocialPreview.py') `
        (Join-Path $root '.github\assets\social-preview.jpg')
    if ($LASTEXITCODE -ne 0) { throw 'GitHub social-preview validation failed.' }
} else {
    Write-Warning 'Python was not available; Archipelago CI will perform Python import and generation tests.'
}
Write-Host "Repository validation passed for version $version."
