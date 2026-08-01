#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
archipelago_path=""
while (($#)); do
    case "$1" in
        --archipelago-path) archipelago_path=${2:?missing value}; shift ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done
[[ -n "$archipelago_path" && -f "$archipelago_path/BaseClasses.py" ]] || {
    printf -- '--archipelago-path must name an Archipelago source checkout.\n' >&2; exit 2;
}
[[ -f "$script_dir/lotf.apworld" ]] || { printf 'lotf.apworld is missing beside this script.\n' >&2; exit 1; }
mkdir -p -- "$archipelago_path/custom_worlds"
cp -- "$script_dir/lotf.apworld" "$archipelago_path/custom_worlds/lotf.apworld"
printf 'Installed lotf.apworld into %s\n' "$archipelago_path/custom_worlds"
