from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Region

from .data import REGION_CONNECTIONS

if TYPE_CHECKING:
    from .world import LordsOfTheFallenWorld


def create_regions(world: "LordsOfTheFallenWorld") -> None:
    names = {name for connection in REGION_CONNECTIONS for name in connection[:2]}
    for name in sorted(names):
        world.multiworld.regions.append(Region(name, world.player, world.multiworld))

    for source, target, _requirement in REGION_CONNECTIONS:
        world.get_region(source).connect(world.get_region(target), f"{source} -> {target}")

