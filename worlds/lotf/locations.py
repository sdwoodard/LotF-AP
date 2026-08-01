from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Location, LocationProgressType
from worlds.generic.Rules import add_item_rule

from .data import GAME, LOCATIONS, LOCATION_NAME_TO_ID, Scope, location_is_unsafe
from .options import MissableLocationBehavior

if TYPE_CHECKING:
    from .world import LordsOfTheFallenWorld


class LordsOfTheFallenLocation(Location):
    game = GAME


def enabled_locations(world: "LordsOfTheFallenWorld"):
    for entry in LOCATIONS:
        if entry.suppress_group == "quest" and not world.options.include_quest_locations:
            continue
        if entry.scope == Scope.STIGMA and not world.options.include_world_stigmas:
            continue
        if (
            location_is_unsafe(entry)
            and world.options.missable_location_behavior == MissableLocationBehavior.option_remove
        ):
            continue
        yield entry


def create_locations(world: "LordsOfTheFallenWorld") -> None:
    for entry in enabled_locations(world):
        region = world.get_region(entry.region)
        location = LordsOfTheFallenLocation(
            world.player,
            entry.name,
            LOCATION_NAME_TO_ID[entry.name],
            region,
        )
        if location_is_unsafe(entry):
            # EXCLUDED keeps both advancement and useful classifications out
            # during normal fill. The explicit rule is defense-in-depth for
            # restrictive fills and future generation paths.
            location.progress_type = LocationProgressType.EXCLUDED
            add_item_rule(location, lambda item: not item.advancement and not item.useful)
        region.locations.append(location)
