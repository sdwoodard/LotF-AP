#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$script_dir/../.." && pwd)
version=$(tr -d '[:space:]' < "$root/VERSION")
skip_validation=0
game_path=""
while (($#)); do
    case "$1" in
        --skip-validation) skip_validation=1 ;;
        --game-path) game_path=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

command -v zip >/dev/null || { printf 'zip is required.\n' >&2; exit 1; }
if ((skip_validation == 0)); then
    args=()
    [[ -n "$game_path" ]] && args+=(--game-path "$game_path")
    bash "$script_dir/test-repository.sh" "${args[@]}"
fi

build="$root/build"
dist="$root/dist"
for directory in "$build" "$dist"; do
    case "$directory" in
        "$root"/*) ;;
        *) printf 'Refusing to clean unexpected path: %s\n' "$directory" >&2; exit 1 ;;
    esac
    rm -rf -- "$directory"
    mkdir -p -- "$directory"
done

apworld_stage="$build/apworld/lotf"
mkdir -p -- "$apworld_stage"
cp -a -- "$root/worlds/lotf/." "$apworld_stage/"
find "$apworld_stage" -type d -name __pycache__ -prune -exec rm -rf -- {} +
(cd "$build/apworld" && zip -qr "$dist/lotf.apworld" lotf)

package_stage="$build/package/LotF-Archipelago-$version"
mkdir -p -- "$package_stage/game-mod/LotFArchipelago"
cp -- "$dist/lotf.apworld" "$package_stage/"
cp -- "$root"/installer/windows/*.ps1 "$root"/installer/windows/*.cmd "$root"/installer/linux/*.sh "$package_stage/"
cp -- "$root/README.md" "$root/LICENSE" "$root/VERSION" "$package_stage/"
cp -- "$root/player-options/Lords of the Fallen.yaml" "$package_stage/"
cp -a -- "$root/game-mod/LotFArchipelago/." "$package_stage/game-mod/LotFArchipelago/"
rm -f -- "$package_stage/game-mod/LotFArchipelago/Assets/README.txt"

linux_package_parent="$build/package-linux"
mkdir -p -- "$linux_package_parent"
cp -a -- "$package_stage" "$linux_package_parent/"
linux_package_stage="$linux_package_parent/LotF-Archipelago-$version"
rm -f -- "$package_stage"/*.sh
rm -f -- "$linux_package_stage"/*.ps1
rm -f -- "$linux_package_stage"/*.cmd

(cd "$build/package" && zip -qr "$dist/LotF-Archipelago-$version-win64.zip" "LotF-Archipelago-$version")
(cd "$linux_package_parent" && zip -qr "$dist/LotF-Archipelago-$version-linux.zip" "LotF-Archipelago-$version")
printf 'Built release artifacts in %s\n' "$dist"
