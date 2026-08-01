from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from worlds.AutoWorld import World

from . import items, locations, regions, rules
from .data import (
    ALL_BOSSES_GOAL_LOCATIONS,
    GAME,
    ITEM_BY_NAME,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    LOCATIONS,
    REGION_PREFIXES,
    location_description,
    location_is_unsafe,
    location_source,
)
from .options import Goal, LordsOfTheFallenOptions
from .web_world import LordsOfTheFallenWebWorld


class LordsOfTheFallenWorld(World):
    """
    Lords of the Fallen is a dark-fantasy action RPG set across the parallel
    realms of Axiom and Umbral. This integration turns unique pickups and
    remembrance stigmas into multiworld checks and can shuffle progression
    keys, quest objects, boss remembrances, and upgrade materials.
    """

    game = GAME
    web = LordsOfTheFallenWebWorld()
    options_dataclass = LordsOfTheFallenOptions
    options: LordsOfTheFallenOptions
    item_name_to_id = ITEM_NAME_TO_ID
    location_name_to_id = LOCATION_NAME_TO_ID
    required_client_version = (0, 6, 7)

    def create_regions(self) -> None:
        regions.create_regions(self)
        locations.create_locations(self)

    def create_items(self) -> None:
        items.create_items(self)

    def create_item(self, name: str) -> items.LordsOfTheFallenItem:
        return items.create_item(self, name)

    def set_rules(self) -> None:
        rules.set_rules(self)

    def get_filler_item_name(self) -> str:
        return "Vigor Cache"

    def fill_slot_data(self) -> Mapping[str, Any]:
        enabled_names = {entry.name for entry in locations.enabled_locations(self)}
        marker_rows = []
        for entry in LOCATIONS:
            suppress = (
                entry.suppress_group == "key" and bool(self.options.shuffle_key_items)
            ) or (
                entry.suppress_group == "quest" and bool(self.options.shuffle_quest_items)
            )
            enabled = entry.name in enabled_names
            if not enabled and not suppress:
                continue
            marker_rows.append(
                {
                    # A zero ID is a suppression-only marker for a location
                    # deliberately removed from the generated pool.
                    "location": LOCATION_NAME_TO_ID[entry.name] if enabled else 0,
                    "marker": entry.marker,
                    "suppress": suppress,
                    "region": entry.region,
                    "prefix": REGION_PREFIXES[entry.region],
                    "description": location_description(entry),
                    "unsafe": location_is_unsafe(entry),
                    "source": location_source(entry),
                }
            )

        item_rows = {
            str(ITEM_NAME_TO_ID[name]): {
                "name": name,
                "asset": data.asset,
                "quantity": data.quantity,
                "unique": data.category in {"key", "quest", "remembrance"},
            }
            for name, data in ITEM_BY_NAME.items()
        }
        goal_locations = []
        if self.options.goal == Goal.option_all_bosses:
            goal_locations = [
                LOCATION_NAME_TO_ID[name] for name in ALL_BOSSES_GOAL_LOCATIONS
            ]
        return {
            "world_version": "0.1.1",
            "markers": marker_rows,
            "items": item_rows,
            "goal_locations": goal_locations,
            "options": self.options.as_dict(
                "goal",
                "shuffle_key_items",
                "shuffle_quest_items",
                "death_link",
                "death_link_amnesty",
                "item_delivery_delay",
            ),
        }
