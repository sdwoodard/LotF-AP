#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
game_path=""
allow_missing_ue4ss=0
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        --allow-missing-ue4ss) allow_missing_ue4ss=1 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
if [[ -z "$game_path" ]]; then
    for candidate in \
        "$HOME/.local/share/Steam/steamapps/common/Lords of the Fallen" \
        "$HOME/.steam/steam/steamapps/common/Lords of the Fallen"; do
        if [[ -f "$candidate/LOTF2/Binaries/Win64/LOTF2-Win64-Shipping.exe" ]]; then game_path=$candidate; break; fi
    done
fi
[[ -n "$game_path" && -f "$game_path/LOTF2/Binaries/Win64/LOTF2-Win64-Shipping.exe" ]] || {
    printf 'Lords of the Fallen was not found; pass --game-path.\n' >&2; exit 1;
}
win64="$game_path/LOTF2/Binaries/Win64"
if [[ ! -f "$win64/ue4ss/UE4SS.dll" && ! -f "$win64/UE4SS.dll" ]]; then
    ((allow_missing_ue4ss)) || { printf 'Install RE-UE4SS 3.x first, or pass --allow-missing-ue4ss.\n' >&2; exit 1; }
    printf 'Warning: UE4SS was not found; staging the mod only.\n' >&2
fi
source_dir="$script_dir/game-mod/LotFArchipelago"
[[ -f "$source_dir/Scripts/main.lua" ]] || source_dir="$script_dir/../game-mod/LotFArchipelago"
[[ -f "$source_dir/Scripts/main.lua" ]] || source_dir="$script_dir/../../game-mod/LotFArchipelago"
[[ -f "$source_dir/Scripts/main.lua" ]] || { printf 'Installer payload is incomplete.\n' >&2; exit 1; }

if [[ -f "$win64/ue4ss/UE4SS.dll" ]]; then
    mods="$win64/ue4ss/Mods"
else
    mods="$win64/Mods"
fi
target="$mods/LotFArchipelago"
mkdir -p -- "$mods"
if [[ -e "$target" ]]; then
    state_home=${XDG_STATE_HOME:-"$HOME/.local/state"}
    backup_root="$state_home/LotFArchipelago/backups"
    mkdir -p -- "$backup_root"
    backup="$backup_root/$(date -u +%Y%m%d-%H%M%S)-$$"
    mv -- "$target" "$backup"
    printf 'Previous mod moved to %s\n' "$backup"
fi
cp -a -- "$source_dir" "$target"
mods_text="$mods/mods.txt"
if [[ -f "$mods_text" ]]; then
    temporary="$mods_text.tmp.$$"
    awk 'BEGIN{found=0} /^[[:space:]]*LotFArchipelago[[:space:]]*:/ {print "LotFArchipelago : 1"; found=1; next} {print} END{if(!found) print "LotFArchipelago : 1"}' "$mods_text" > "$temporary"
    mv -- "$temporary" "$mods_text"
fi
printf 'Installed LotF Archipelago into %s\n' "$target"
printf 'Use this mod offline only; do not use matchmaking, co-op, invasions, or Easy Anti-Cheat.\n'
