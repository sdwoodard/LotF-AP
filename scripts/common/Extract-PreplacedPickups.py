#!/usr/bin/env python3
"""Extract stable pickup GUIDs from the retail pre-placed-loot data asset.

The input must be a UE5.1 legacy ``.uasset``/``.uexp`` pair produced from
``DA_PrePlacedRandomLootMap`` by retoc.  The generated Python module is checked
in so generation and client use never need access to a player's game files.
"""

from __future__ import annotations

import argparse
import struct
from collections import Counter
from pathlib import Path


REGIONS = {
    "CliffsideCity1": "Pilgrim's Perch",
    "CliffsideCity2": "Pilgrim's Perch",
    "DeepMines": "Revelation Depths",
    "Grove": "Abandoned Redcopse",
    "HighSee": "The Empyrean",
    "IceForest": "Fief of the Chill Curse",
    "LowerCity": "Lower Calrath",
    "Manse": "Manse of the Hallowed Brothers",
    "Mines": "Sunless Skein",
    "PenitentRoad": "Path of Devotion",
    "PenitentTower": "Tower of Penance",
    "Quest": "Defiled Sepulchre",
    "RhogarCastle": "Bramis Castle",
    "SkywalkBridge": "Skyrest Bridge",
    "Swamp": "Forsaken Fen",
    "SwampLCityConnector": "Fitzroy's Gorge",
    "UpperCityA": "Upper Calrath",
    "UpperCityB": "Upper Calrath",
    "WomenArea": "Abbey of the Hallowed Sisters",
}

REGION_ORDER = {name: index for index, name in enumerate(REGIONS.values())}
EXCLUDED_ROWS = {
    # The tutorial Throwing Stone must remain vanilla so hanging-corpse items
    # can always be knocked down before the Archipelago bridge is connected.
    "816_Quest_QST_Quest": "B21D92B8406214F0AEAF6B9B239BB661",
}


def read_name_map(data: bytes) -> list[str]:
    """Read the FName map fields used by UE5.1's package summary."""
    if data[:4] != bytes.fromhex("c1832a9e"):
        raise ValueError("input is not a legacy Unreal package")
    # UE5's versioned package summary is not naturally aligned. These fields
    # are at 0x63/0x67 for this converted retail asset.
    name_count = struct.unpack_from("<I", data, 0x63)[0]
    name_offset = struct.unpack_from("<I", data, 0x67)[0]
    if not 1 <= name_count <= 100_000 or not 0 < name_offset < len(data):
        raise ValueError("invalid UE5.1 package name-map metadata")
    names: list[str] = []
    cursor = name_offset
    for _ in range(name_count):
        length = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        if length < 0:
            size = -length * 2
            value = data[cursor : cursor + size].decode("utf-16-le").rstrip("\0")
        else:
            size = length
            value = data[cursor : cursor + size].rstrip(b"\0").decode("utf-8")
        cursor += size + 4  # serialized string plus case-preserving name hashes
        names.append(value)
    return names


def guid_string(raw: bytes) -> str:
    a, b, c, d = struct.unpack("<IIII", raw)
    return f"{a:08X}{b:08X}{c:08X}{d:08X}"


def read_rows(uasset: Path) -> list[tuple[str, str]]:
    names = read_name_map(uasset.read_bytes())
    export = uasset.with_suffix(".uexp").read_bytes()
    count = struct.unpack_from("<I", export, 6)[0]
    cursor = 10
    result: list[tuple[str, str]] = []
    for _ in range(count):
        guid = guid_string(export[cursor : cursor + 16])
        name_index = struct.unpack_from("<I", export, cursor + 22)[0]
        if name_index >= len(names):
            raise ValueError(f"row refers to missing FName index {name_index}")
        result.append((names[name_index], guid))
        cursor += 30
    if export[cursor:] != b"\0\0\0\0" + bytes.fromhex("c1832a9e"):
        raise ValueError("unexpected pre-placed-loot export layout or footer")
    return result


def location_rows(uasset: Path) -> list[tuple[str, str, str, str, str, str, bool]]:
    all_rows = read_rows(uasset)
    observed_exclusions = {name: guid for name, guid in all_rows if name in EXCLUDED_ROWS}
    if observed_exclusions != EXCLUDED_ROWS:
        raise ValueError(
            "tutorial Throwing Stone identity changed: "
            f"expected {EXCLUDED_ROWS!r}, observed {observed_exclusions!r}"
        )
    raw_rows = [row for row in all_rows if row[0] not in EXCLUDED_ROWS]
    parsed = []
    duplicates = Counter(name for name, _guid in raw_rows)
    seen: Counter[str] = Counter()
    for row_name, guid in raw_rows:
        number, internal_region, realm_code, difficulty = row_name.split("_", 3)
        region = REGIONS[internal_region]
        realm = {"AX": "Axiom", "UM": "Umbral", "QST": "Quest"}[realm_code]
        difficulty_text = {
            "VeryEasy": "very easy",
            "Easy": "easy",
            "Moderate": "moderate",
            "Difficult": "difficult",
            "VeryDifficult": "very difficult",
            "Quest": "quest",
        }[difficulty]
        seen[row_name] += 1
        suffix = f" {seen[row_name]}" if duplicates[row_name] > 1 else ""
        name = f"{region} - Pickup {number} ({realm}{suffix})"
        description = f"Pre-placed {realm} pickup {number} in {region}."
        parsed.append((name, region, guid, row_name, realm, description, realm_code == "QST"))
    parsed.sort(key=lambda row: (REGION_ORDER[row[1]], int(row[0].split("Pickup ", 1)[1].split()[0]), row[2]))
    return parsed


def render(rows: list[tuple[str, str, str, str, str, str, bool]]) -> str:
    lines = [
        '"""Generated pickup identities for Steam build 24429019.',
        "",
        "Do not edit by hand. Regenerate with scripts/common/Extract-PreplacedPickups.py.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# name, region, normalized FGuid, retail row label, description, quest/missable",
        "PREPLACED_PICKUPS: tuple[tuple[str, str, str, str, str, bool], ...] = (",
    ]
    for name, region, guid, row_name, _realm, description, quest in rows:
        lines.append(f"    ({name!r}, {region!r}, {guid!r}, {row_name!r}, {description!r}, {quest!r}),")
    lines.extend((")", ""))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("uasset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = location_rows(args.uasset)
    if len(rows) != 597:
        raise SystemExit(f"expected 597 eligible pickups, extracted {len(rows)}")
    args.output.write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"Wrote {len(rows)} pickup identities to {args.output}")


if __name__ == "__main__":
    main()
