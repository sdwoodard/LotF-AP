#!/usr/bin/env bash
set -euo pipefail

game_path=""
data_root=${LOTF_AP_DATA_DIR:-"${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago"}
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
if [[ -z "$game_path" && -f "$data_root/game-path.txt" ]]; then
    IFS= read -r game_path < "$data_root/game-path.txt"
fi
[[ -n "$game_path" && -d "$game_path/LOTF2/Binaries/Win64" ]] || { printf 'No saved installation was found.\n' >&2; exit 2; }
win64=$(cd -- "$game_path/LOTF2/Binaries/Win64" && pwd)
for mods in "$win64/ue4ss/Mods" "$win64/Mods"; do
    target="$mods/LotFArchipelago"
    case "$target" in "$mods"/LotFArchipelago) ;; *) printf 'Refusing unexpected target.\n' >&2; exit 1;; esac
    [[ ! -e "$target" ]] || rm -rf -- "$target"
    mods_text="$mods/mods.txt"
    if [[ -f "$mods_text" ]]; then
        temporary="$mods_text.tmp.$$"
        grep -Ev '^[[:space:]]*LotFArchipelago[[:space:]]*:' "$mods_text" > "$temporary" || true
        mv -- "$temporary" "$mods_text"
    fi
done
rm -f -- "$data_root/game-path.txt"
printf 'Removed LotF Archipelago; UE4SS and other mods were left unchanged.\n'
