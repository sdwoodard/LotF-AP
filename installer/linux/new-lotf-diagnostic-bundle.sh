#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
multiworld=""
player_yaml=""
game_path=""
output=""
while (($#)); do
    case "$1" in
        --multiworld) multiworld=${2:?missing value}; shift ;;
        --player-yaml) player_yaml=${2:?missing value}; shift ;;
        --game-path) game_path=${2:?missing value}; shift ;;
        --output) output=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
command -v zip >/dev/null || { printf 'zip is required.\n' >&2; exit 1; }
data_root=${LOTF_AP_DATA_DIR:-"${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago"}
[[ -d "$data_root" ]] || { printf 'No diagnostic data exists at %s\n' "$data_root" >&2; exit 1; }
if [[ -z "$game_path" && -f "$data_root/game-path.txt" ]]; then
    IFS= read -r game_path < "$data_root/game-path.txt"
fi
[[ -n "$output" ]] || output="$PWD/LotF-AP-Diagnostics-$(date -u +%Y%m%d-%H%M%S).zip"
case "$output" in /*) ;; *) output="$PWD/$output" ;; esac
[[ ! -e "$output" ]] || { printf 'Output already exists: %s\n' "$output" >&2; exit 1; }
temporary=$(mktemp -d -t lotf-ap-diagnostics.XXXXXXXX)
trap 'rm -rf -- "$temporary"' EXIT
for directory in logs recovery bridge; do [[ ! -e "$data_root/$directory" ]] || cp -a -- "$data_root/$directory" "$temporary/"; done
[[ ! -f "$data_root/state.txt" ]] || cp -- "$data_root/state.txt" "$temporary/"
mkdir -p -- "$temporary/attachments"
[[ -z "$multiworld" ]] || cp -- "$multiworld" "$temporary/attachments/multiworld-$(basename "$multiworld")"
[[ -z "$player_yaml" ]] || cp -- "$player_yaml" "$temporary/attachments/player-yaml-$(basename "$player_yaml")"

game_summary="Game executable: not supplied"
if [[ -n "$game_path" ]]; then
    exe="$game_path/LOTF2/Binaries/Win64/LOTF2-Win64-Shipping.exe"
    if [[ -f "$exe" ]]; then
        game_summary="Game executable SHA-256: $(sha256sum "$exe" | cut -d' ' -f1)\nGame executable size: $(stat -c %s "$exe") bytes\nGame executable modified UTC: $(date -u -r "$exe" +%Y-%m-%dT%H:%M:%SZ)"
    fi
    [[ ! -f "$game_path/LOTF2/Binaries/Win64/UE4SS.log" ]] || cp -- "$game_path/LOTF2/Binaries/Win64/UE4SS.log" "$temporary/"
    [[ ! -f "$game_path/LOTF2/Binaries/Win64/ue4ss/UE4SS.log" ]] || cp -- "$game_path/LOTF2/Binaries/Win64/ue4ss/UE4SS.log" "$temporary/UE4SS-current-layout.log"
fi
version_file="$script_dir/VERSION"
[[ -f "$version_file" ]] || version_file="$script_dir/../VERSION"
[[ -f "$version_file" ]] || version_file="$script_dir/../../VERSION"
version=$([[ -f "$version_file" ]] && tr -d '[:space:]' < "$version_file" || printf unknown)
printf 'Created UTC: %s\nLotF AP version: %s\n%b\nLinux: %s\nMultiworld attached: %s\nPlayer YAML attached: %s\n\nThis bundle intentionally contains no Lords of the Fallen save file.\nReview optional attachments before sharing.\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$version" "$game_summary" "$(uname -a)" "$([[ -n "$multiworld" ]] && printf yes || printf no)" "$([[ -n "$player_yaml" ]] && printf yes || printf no)" > "$temporary/SUMMARY.txt"
(cd "$temporary" && zip -qr "$output" .)
printf 'Created diagnostic bundle: %s\n' "$output"
