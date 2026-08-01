#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(cd -- "$script_dir/../.." && pwd)
archipelago_path=""
apworld_path="$root/dist/lotf.apworld"
report="$root/test-results/generation-matrix.json"
python_cmd=${PYTHON:-python3}
extra=()
while (($#)); do
    case "$1" in
        --archipelago-path) archipelago_path=${2:?missing value}; shift ;;
        --apworld-path) apworld_path=${2:?missing value}; shift ;;
        --report) report=${2:?missing value}; shift ;;
        --python) python_cmd=${2:?missing value}; shift ;;
        --seed|--solo-cases|--same-game-cases|--same-game-slots|--mixed-cases|--mixed-lotf-slots)
            extra+=("$1" "${2:?missing value}"); shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
[[ -n "$archipelago_path" && -f "$archipelago_path/BaseClasses.py" ]] || {
    printf -- '--archipelago-path must name an Archipelago source checkout.\n' >&2; exit 2;
}
[[ -f "$apworld_path" ]] || { printf 'APWorld not found: %s\n' "$apworld_path" >&2; exit 1; }
mkdir -p "$archipelago_path/custom_worlds" "$(dirname "$report")"
cp -- "$apworld_path" "$archipelago_path/custom_worlds/lotf.apworld"
SKIP_REQUIREMENTS_UPDATE=1 "$python_cmd" "$script_dir/../common/Test-GenerationMatrix.py" \
    --archipelago-path "$archipelago_path" --report "$report" "${extra[@]}"
printf 'Generation matrix passed. Report: %s\n' "$report"
