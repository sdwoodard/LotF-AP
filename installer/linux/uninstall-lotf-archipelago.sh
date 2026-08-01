#!/usr/bin/env bash
set -euo pipefail

game_path=""
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
[[ -n "$game_path" && -d "$game_path/LOTF2/Binaries/Win64" ]] || { printf -- '--game-path is required.\n' >&2; exit 2; }
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
printf 'Removed LotF Archipelago; UE4SS and other mods were left unchanged.\n'
