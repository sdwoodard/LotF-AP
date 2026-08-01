from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import ItemClassification
from worlds.generic.Rules import set_rule

from .data import ALL_BOSSES_GOAL_LOCATIONS, GAME, REGION_CONNECTIONS
from .items import LordsOfTheFallenItem
from .logic import requirement_is_active
from .options import Goal

if TYPE_CHECKING:
    from .world import LordsOfTheFallenWorld


def set_rules(world: "LordsOfTheFallenWorld") -> None:
    for source, target, requirement in REGION_CONNECTIONS:
        if requirement_is_active(
            requirement,
            shuffle_key_items=bool(world.options.shuffle_key_items),
            shuffle_quest_items=bool(world.options.shuffle_quest_items),
        ):
            entrance = world.get_entrance(f"{source} -> {target}")
            set_rule(
                entrance,
                lambda state, item=requirement: state.has(item, world.player),
            )

    goal_region_name = (
        "Bramis Castle" if world.options.goal == Goal.option_any_ending else "Menu"
    )
    goal_region = world.get_region(goal_region_name)
    victory_location = LordsOfTheFallenLocation(
        world.player, "Victory", None, goal_region
    )
    if world.options.goal == Goal.option_all_bosses:
        set_rule(
            victory_location,
            lambda state: all(
                state.can_reach(location_name, "Location", world.player)
                for location_name in ALL_BOSSES_GOAL_LOCATIONS
            ),
        )
    victory_location.place_locked_item(
        LordsOfTheFallenItem(
            "Victory", ItemClassification.progression, None, world.player
        )
    )
    goal_region.locations.append(victory_location)
    world.multiworld.completion_condition[world.player] = lambda state: state.has(
        "Victory", world.player
    )


# Import at end to keep the TYPE_CHECKING path above cycle-free.
from .locations import LordsOfTheFallenLocation
