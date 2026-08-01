#!/usr/bin/env python3
"""Resolve retail pre-placed pickup GUIDs to cooked gameplay sublevels.

This developer tool reads a local Lords of the Fallen installation with
``retoc``. It does not modify the game. The report makes location-logic review
reproducible: every GUID in ``preplaced_pickups.py`` must resolve to exactly one
cooked map (apart from explicitly reviewed duplicate references).
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


LIST_ROW = re.compile(
    r"^\S+\s+(?P<chunk>[0-9a-f]{24})\s+\S+\s+ExportBundleData\s+\d+\s+(?P<path>.+\.umap)$",
    re.IGNORECASE,
)

# This actor is referenced by two Bramis Castle level instances. Any other
# multi-map GUID is new evidence that must be reviewed before generation logic
# can safely consume it.
REVIEWED_DUPLICATE_GUIDS = {"1995C690487653B5B70EDC9F2B27F630"}


@dataclass(frozen=True)
class CookedMap:
    container: Path
    chunk: str
    package_path: str


class GuidMatcher:
    """Wu-Manber-style exact matcher for the fixed 16-byte FGuid patterns."""

    pattern_size = 16
    block_size = 3

    def __init__(self, patterns: set[bytes]) -> None:
        self.default_shift = self.pattern_size - self.block_size + 1
        self.shifts: dict[bytes, int] = {}
        self.suffixes: dict[bytes, list[bytes]] = {}
        last_block = self.pattern_size - self.block_size
        for pattern in patterns:
            if len(pattern) != self.pattern_size:
                raise ValueError("every FGuid pattern must be 16 bytes")
            for offset in range(last_block + 1):
                block = pattern[offset : offset + self.block_size]
                shift = last_block - offset
                self.shifts[block] = min(shift, self.shifts.get(block, self.default_shift))
            self.suffixes.setdefault(pattern[-self.block_size :], []).append(pattern)

    def find(self, payload: bytes) -> set[bytes]:
        found: set[bytes] = set()
        end = self.pattern_size - 1
        payload_size = len(payload)
        while end < payload_size:
            block = payload[end - self.block_size + 1 : end + 1]
            shift = self.shifts.get(block, self.default_shift)
            if shift:
                end += shift
                continue
            start = end - self.pattern_size + 1
            candidate = payload[start : end + 1]
            for pattern in self.suffixes.get(block, ()):
                if candidate == pattern:
                    found.add(pattern)
                    break
            end += 1
        return found


def load_pickups(module_path: Path) -> tuple[tuple[str, str, str, str, str, bool], ...]:
    spec = importlib.util.spec_from_file_location("lotf_preplaced_pickups", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PREPLACED_PICKUPS


def list_maps(retoc: Path, containers: list[Path]) -> list[CookedMap]:
    maps: dict[str, CookedMap] = {}
    for container in containers:
        result = subprocess.run(
            [str(retoc), "list", "--all", "--path", "--package", "--size", str(container)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for raw_line in result.stdout.splitlines():
            match = LIST_ROW.match(raw_line.strip())
            if not match:
                continue
            package_path = match.group("path").replace("\\", "/")
            if "/World/" not in package_path or "/Maps/" not in package_path:
                continue
            if package_path.endswith("_BuiltData.umap"):
                continue
            maps[package_path.lower()] = CookedMap(container, match.group("chunk"), package_path)
    return sorted(maps.values(), key=lambda entry: entry.package_path.lower())


def guid_bytes(guid: str) -> bytes:
    return struct.pack("<IIII", *(int(guid[index : index + 8], 16) for index in range(0, 32, 8)))


def scan_map(retoc: Path, cooked_map: CookedMap, matcher: GuidMatcher) -> tuple[str, set[bytes]]:
    result = subprocess.run(
        [str(retoc), "get", str(cooked_map.container), cooked_map.chunk, "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cooked_map.package_path, matcher.find(result.stdout)


def scan_legacy_map(root: Path, map_path: Path, matcher: GuidMatcher) -> tuple[str, set[bytes]]:
    export_path = map_path.with_suffix(".uexp")
    payload = map_path.read_bytes()
    if export_path.exists():
        payload += export_path.read_bytes()
    package_path = "../../../" + map_path.relative_to(root).as_posix()
    return package_path, matcher.find(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retoc", type=Path)
    parser.add_argument("--paks", type=Path)
    parser.add_argument(
        "--legacy-maps",
        type=Path,
        help="Directory from one `retoc to-legacy --filter .umap` pass",
    )
    parser.add_argument(
        "--pickups",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "worlds" / "lotf" / "preplaced_pickups.py",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    pickups = load_pickups(args.pickups)
    by_raw_guid = {guid_bytes(row[2]): row for row in pickups}
    if len(by_raw_guid) != len(pickups):
        raise SystemExit("pickup table contains duplicate GUIDs")
    matcher = GuidMatcher(set(by_raw_guid))

    matches: dict[bytes, list[str]] = {raw_guid: [] for raw_guid in by_raw_guid}
    if args.legacy_maps:
        maps: list[Path] = sorted(
            path
            for path in args.legacy_maps.rglob("*.umap")
            if re.search(r"_(?:GAM|UMB)_", path.stem, re.IGNORECASE)
        )
        submit = lambda executor, map_path: executor.submit(
            scan_legacy_map, args.legacy_maps, map_path, matcher
        )
    else:
        if not args.retoc or not args.paks:
            parser.error("provide --legacy-maps or both --retoc and --paks")
        containers = sorted(args.paks.glob("*.utoc"))
        if not containers:
            raise SystemExit(f"no .utoc files found in {args.paks}")
        cooked_maps = list_maps(args.retoc, containers)
        maps = cooked_maps
        submit = lambda executor, cooked_map: executor.submit(scan_map, args.retoc, cooked_map, matcher)
    if not maps:
        raise SystemExit("no cooked maps found")
    print(f"Scanning {len(maps)} cooked maps for {len(pickups)} pickup GUIDs...", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        pending = {submit(executor, cooked_map): cooked_map for cooked_map in maps}
        for completed, future in enumerate(as_completed(pending), 1):
            package_path, found = future.result()
            for raw_guid in found:
                matches[raw_guid].append(package_path)
            if completed % 50 == 0:
                print(f"  scanned {completed}/{len(maps)} maps", file=sys.stderr)

    rows: list[tuple[str, str, str, str, str]] = []
    for raw_guid, pickup in by_raw_guid.items():
        name, broad_region, guid, retail_row, _description, _quest = pickup
        resolved = sorted(set(matches[raw_guid]))
        rows.append((guid, retail_row, name, broad_region, " | ".join(resolved)))

    if args.output and args.output.suffix.lower() == ".py":
        lines = [
            '\"\"\"Generated retail pickup-to-sublevel audit for Steam build 24429019.',
            "",
            "Regenerate with scripts/common/Audit-PickupSublevels.py; do not edit by hand.",
            '\"\"\"',
            "",
            "from __future__ import annotations",
            "",
            "# Normalized FGuid -> one or more cooked gameplay map package paths.",
            "PICKUP_SUBLEVELS: dict[str, tuple[str, ...]] = {",
        ]
        for guid, _retail_row, _name, _region, cooked_maps in rows:
            paths = tuple(cooked_maps.split(" | ")) if cooked_maps else ()
            lines.append(f"    {guid!r}: {paths!r},")
        lines.extend(("}", ""))
        args.output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    else:
        stream = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
        try:
            writer = csv.writer(stream)
            writer.writerow(("guid", "retail_row", "location_name", "broad_region", "cooked_maps"))
            writer.writerows(rows)
        finally:
            if args.output:
                stream.close()

    unresolved = sum(not row[-1] for row in rows)
    duplicate_guids = {row[0] for row in rows if " | " in row[-1]}
    print(
        f"Resolved {len(rows) - unresolved}/{len(rows)} pickups; "
        f"{unresolved} unresolved and {len(duplicate_guids)} with multiple map references.",
        file=sys.stderr,
    )
    if duplicate_guids != REVIEWED_DUPLICATE_GUIDS:
        print(
            "Unreviewed duplicate-map GUID set: "
            f"expected {sorted(REVIEWED_DUPLICATE_GUIDS)}, got {sorted(duplicate_guids)}",
            file=sys.stderr,
        )
    raise SystemExit(
        1 if unresolved or duplicate_guids != REVIEWED_DUPLICATE_GUIDS else 0
    )


if __name__ == "__main__":
    main()
