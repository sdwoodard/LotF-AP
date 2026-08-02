#!/usr/bin/env bash
set -euo pipefail

game_path=""
proton=""
compat_data=""
dry_run=0
while (($#)); do
    case "$1" in
        --game-path) game_path=${2:?missing value}; shift ;;
        --proton) proton=${2:?missing value}; shift ;;
        --compat-data) compat_data=${2:?missing value}; shift ;;
        --dry-run) dry_run=1 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
data_root=${LOTF_AP_DATA_DIR:-"${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago"}
if [[ -z "$game_path" && -f "$data_root/game-path.txt" ]]; then
    IFS= read -r game_path < "$data_root/game-path.txt"
fi
[[ -n "$game_path" ]] || { printf 'No saved installation was found; run the installer first.\n' >&2; exit 2; }
game_path=$(cd -- "$game_path" && pwd)
exe="$game_path/LOTF2/Binaries/Win64/LOTF2-Win64-Shipping.exe"
[[ -f "$exe" ]] || { printf 'Shipping executable was not found.\n' >&2; exit 1; }
if pgrep -afi 'EasyAntiCheat|start_protected_game' >/dev/null; then
    printf 'Easy Anti-Cheat is running; close it first.\n' >&2; exit 1
fi
for app_id_file in "$game_path/steam_appid.txt" "$(dirname -- "$exe")/steam_appid.txt"; do
    [[ ! -e "$app_id_file" ]] || { printf 'Remove unsupported file: %s\n' "$app_id_file" >&2; exit 1; }
done
steamapps=$(cd -- "$game_path/../.." && pwd)
steam_root=$(cd -- "$steamapps/.." && pwd)
[[ -n "$compat_data" ]] || compat_data="$steamapps/compatdata/1501750"
if [[ -z "$proton" ]]; then
    proton=$(find "$steam_root/compatibilitytools.d" "$steamapps/common" -maxdepth 3 -type f -name proton -print 2>/dev/null | sort -V | tail -n 1 || true)
fi
[[ -n "$proton" && -x "$proton" ]] || { printf 'Proton was not found; pass --proton /path/to/proton.\n' >&2; exit 1; }

mkdir -p -- "$data_root"
data_root=$(cd -- "$data_root" && pwd)
windows_data_root="Z:${data_root//\//\\}"
command=(env "SteamAppId=1501750" "SteamGameId=1501750" "EOS_DISABLE_OVERLAY=1" "STEAM_COMPAT_DATA_PATH=$compat_data" "STEAM_COMPAT_CLIENT_INSTALL_PATH=$steam_root" "LOTF_AP_GAME_DATA_DIR=$windows_data_root" "$proton" run "$exe" -NoEAC -Offline -NoRedpointEOS -NoOnlineSubsystemRedpointEOS)
printf 'Starting the shipping executable with anti-cheat and Redpoint EOS disabled.\n'
if ((dry_run)); then printf '%q ' "${command[@]}"; printf '\n'; exit 0; fi
exec "${command[@]}"
