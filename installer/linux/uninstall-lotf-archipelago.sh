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
cache_path_state="$data_root/ue4ss-settings-path.txt"
cache_previous_state="$data_root/ue4ss-cache-previous.txt"
if [[ -f "$cache_path_state" && -f "$cache_previous_state" ]]; then
    IFS= read -r ue4ss_settings < "$cache_path_state"
    IFS= read -r previous < "$cache_previous_state"
    case "$ue4ss_settings" in
        "$win64"/ue4ss/UE4SS-settings.ini|"$win64"/UE4SS-settings.ini) ;;
        *) printf 'Refusing a UE4SS settings path outside the game folder: %s\n' "$ue4ss_settings" >&2; exit 1 ;;
    esac
    if [[ -f "$ue4ss_settings" ]]; then
        temporary_settings="$ue4ss_settings.tmp.$$"
        restored=0
        : > "$temporary_settings"
        while IFS= read -r line || [[ -n "$line" ]]; do
            if [[ "$line" =~ ^([[:space:]]*bUseUObjectArrayCache[[:space:]]*=[[:space:]])(false|0)(.*)$ ]]; then
                if [[ "$previous" != "__absent__" ]]; then
                    printf '%s%s%s\n' "${BASH_REMATCH[1]}" "$previous" "${BASH_REMATCH[3]}" >> "$temporary_settings"
                fi
                restored=1
            else
                printf '%s\n' "$line" >> "$temporary_settings"
            fi
        done < "$ue4ss_settings"
        if ((restored)); then
            mv -- "$temporary_settings" "$ue4ss_settings"
            printf 'Restored the UE4SS object-array cache setting that existed before installation.\n'
        else
            rm -f -- "$temporary_settings"
            printf 'UE4SS object-array cache setting was changed after installation; left it unchanged.\n'
        fi
    fi
fi
rm -f -- "$data_root/game-path.txt"
rm -f -- "$cache_path_state" "$cache_previous_state"
printf 'Removed LotF Archipelago; UE4SS and other mods were left unchanged.\n'
