#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$script_dir/../.." && pwd)
game_path=""
retoc_path=""
python_cmd=${PYTHON:-python3}
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        --retoc-path) retoc_path=${2:?missing value}; shift ;;
        --python) python_cmd=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

command -v "$python_cmd" >/dev/null || { printf '%s is required.\n' "$python_cmd" >&2; exit 1; }
version=$(tr -d '[:space:]' < "$root/VERSION")
grep -Fq "\"world_version\": \"$version\"" "$root/worlds/lotf/archipelago.json"
grep -Fq "\"world_version\": \"$version\"" "$root/worlds/lotf/world.py"
grep -Eq "version[[:space:]]*=[[:space:]]*\"$version\"" "$root/game-mod/LotFArchipelago/Scripts/bridge.lua"
for pickup_runtime_path in Pickup:PickupSetupFinished Pickup:Show Pickup:TryTakePickup 'LoadAsset(load_path)'; do
    grep -Fq "$pickup_runtime_path" "$root/game-mod/LotFArchipelago/Scripts/bridge.lua"
done
for unsafe_pickup_path in subsystem.RegisteredPickups 'pickups:ForEach' 'NotifyOnNewObject(' 'FindAllOf("Pickup")' pickup_scan asset_classes 'archipelago_icon = texture'; do
    if grep -Fq "$unsafe_pickup_path" "$root/game-mod/LotFArchipelago/Scripts/bridge.lua"; then
        printf 'Lua bridge retains unsafe pickup/object-lifetime path: %s\n' "$unsafe_pickup_path" >&2
        exit 1
    fi
done

required=(
    worlds/lotf/__init__.py
    worlds/lotf/world.py
    worlds/lotf/assets/lotf-icon.png
    worlds/lotf/client/client.py
    .github/assets/social-preview.jpg
    game-mod/LotFArchipelago/Scripts/main.lua
    game-mod/LotFArchipelago/Assets/archipelago.png
    installer/linux/install-lotf-archipelago.sh
)
for relative in "${required[@]}"; do
    [[ -f "$root/$relative" ]] || { printf 'Required file is missing: %s\n' "$relative" >&2; exit 1; }
done

while IFS= read -r file; do bash -n "$file"; done < <(find "$root/scripts" "$root/installer" -type f -name '*.sh' -print)
"$python_cmd" -m compileall -q "$root/worlds/lotf"
"$python_cmd" "$root/scripts/common/Validate-PngAlpha.py" \
    "$root/game-mod/LotFArchipelago/Assets/archipelago.png" \
    "$root/worlds/lotf/assets/lotf-icon.png" \
    "$root/.github/assets/lotf-icon.png"
"$python_cmd" "$root/scripts/common/Validate-SocialPreview.py" \
    "$root/.github/assets/social-preview.jpg"
if grep -Fqi 'Windows-Installer' "$root/scripts/windows/Build-Release.ps1"; then
    printf 'The separate Windows installer archive must not be built.\n' >&2
    exit 1
fi
if grep -Fq 'ReleaseZip' "$root/installer/windows/Install-LotFArchipelago.ps1"; then
    printf 'The Windows installer must not ask for a release package.\n' >&2
    exit 1
fi
grep -Fq 'game-mod\LotFArchipelago' "$root/installer/windows/Install-LotFArchipelago.ps1"
grep -Fq 'bUseUObjectArrayCache' "$root/installer/windows/Install-LotFArchipelago.ps1"
grep -Fq 'ue4ss_object_array_cache_previous' "$root/installer/windows/Install-LotFArchipelago.ps1"
grep -Fq 'Restore-Ue4ssCompatibility' "$root/installer/windows/Uninstall-LotFArchipelago.ps1"
grep -Fq 'bUseUObjectArrayCache' "$root/installer/linux/install-lotf-archipelago.sh"
grep -Fq 'ue4ss-cache-previous.txt' "$root/installer/linux/uninstall-lotf-archipelago.sh"
if grep -Eq 'cp .*(CHANGELOG\.md|docs/\.)' "$root/scripts/linux/build-release.sh"; then
    printf 'Player release archives must not contain repository-only changelog or developer documentation.\n' >&2
    exit 1
fi
grep -Fq 'Assets/README.txt' "$root/scripts/linux/build-release.sh"
for offline_setting in -NoEAC -Offline -NoRedpointEOS -NoOnlineSubsystemRedpointEOS; do
    grep -Fq -- "$offline_setting" "$root/installer/windows/Start-LotF-AP.ps1"
    grep -Fq -- "$offline_setting" "$root/installer/linux/start-lotf-ap.sh"
done

if [[ -n "$game_path" ]]; then
    executable="$game_path/LOTF2/Binaries/Win64/LOTF2-Win64-Shipping.exe"
    utoc="$game_path/LOTF2/Content/Paks/pakchunk0-Windows.utoc"
    global_utoc="$game_path/LOTF2/Content/Paks/global.utoc"
    for file in "$executable" "$utoc" "$global_utoc"; do
        [[ -f "$file" ]] || { printf 'Game file is missing: %s\n' "$file" >&2; exit 1; }
    done
    executable_hash=$(sha256sum "$executable" | cut -d' ' -f1 | tr '[:lower:]' '[:upper:]')
    executable_size=$(stat -c %s "$executable")
    grep -Fq "$executable_hash" "$root/docs/GAME_BUILD.md" || { printf 'Executable hash is not documented; audit this game update first.\n' >&2; exit 1; }
    grep -Fq "$executable_size" "$root/docs/GAME_BUILD.md" || { printf 'Executable size is not documented; audit this game update first.\n' >&2; exit 1; }
    printf 'Validated documented game executable: sha256=%s size=%s\n' "$executable_hash" "$executable_size"
    if [[ -n "$retoc_path" ]]; then
        "$retoc_path" list --path "$utoc" >/dev/null
        "$retoc_path" print-script-objects "$global_utoc" >/dev/null
        printf 'retoc opened both IoStore indexes successfully.\n'
    fi
fi
printf 'Repository validation passed for version %s.\n' "$version"
