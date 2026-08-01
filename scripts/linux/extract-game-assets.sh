#!/usr/bin/env bash
set -euo pipefail

game_path=""
retoc_path=""
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        --retoc-path) retoc_path=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
[[ -n "$game_path" && -n "$retoc_path" ]] || {
    printf 'Usage: %s --game-path PATH --retoc-path PATH\n' "$0" >&2; exit 2;
}
utoc="$game_path/LOTF2/Content/Paks/pakchunk0-Windows.utoc"
[[ -f "$utoc" && -x "$retoc_path" ]] || { printf 'Game IoStore or retoc executable is missing.\n' >&2; exit 1; }
"$retoc_path" list --path "$utoc" \
    | grep -oE '\.\./\.\./\.\./LOTF2/Content/Blueprints/Data/Equipment/Items/[^[:space:]]+\.uasset' \
    | sort -u
