from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification, LocationProgressType

from .data import GAME, ITEM_BY_NAME, ITEM_NAME_TO_ID

if TYPE_CHECKING:
    from .world import LordsOfTheFallenWorld


class LordsOfTheFallenItem(Item):
    game = GAME


VANILLA_WEAPON_UPGRADE_SEQUENCE = (
    ("Small Deralium Fragment",) * 2
    + ("Regular Deralium Nugget",) * 7
    + ("Large Deralium Shard",) * 20
    + ("Deralium Chunk",)
)


def create_item(world: "LordsOfTheFallenWorld", name: str) -> LordsOfTheFallenItem:
    data = ITEM_BY_NAME[name]
    if data.progression:
        classification = ItemClassification.progression
    elif data.useful:
        classification = ItemClassification.useful
    else:
        classification = ItemClassification.filler
    return LordsOfTheFallenItem(name, classification, ITEM_NAME_TO_ID[name], world.player)


def create_items(world: "LordsOfTheFallenWorld") -> None:
    location_count = len(world.multiworld.get_unfilled_locations(world.player))
    names: list[str] = []

    if world.options.shuffle_key_items:
        names.extend(item.name for item in ITEM_BY_NAME.values() if item.category == "key")

    if world.options.shuffle_quest_items:
        names.extend(item.name for item in ITEM_BY_NAME.values() if item.category == "quest")

    if world.options.remembrance_items:
        remembrance_names = [item.name for item in ITEM_BY_NAME.values() if item.category == "remembrance"]
        names.extend(remembrance_names)

    names.extend(VANILLA_WEAPON_UPGRADE_SEQUENCE[: world.options.weapon_upgrade_items.value])
    names.extend("Saintly Quintessence" for _ in range(world.options.sanguinarix_upgrade_items.value))
    names.extend("Antediluvian Chisel" for _ in range(world.options.lamp_upgrade_items.value))

    # Highly constrained location pools should still generate. Preserve the
    # traversal items used by rules, then deterministically trim useful extras.
    if len(names) > location_count:
        required = {item.name for item in ITEM_BY_NAME.values() if item.progression}
        required_names = [name for name in names if name in required]
        optional_names = [name for name in names if name not in required]
        names = (required_names + optional_names)[:location_count]

    filler_cycle = tuple(
        item.name
        for item in ITEM_BY_NAME.values()
        if item.category == "filler" and item.name != "Vigor Cache"
    )
    names.extend(
        filler_cycle[index % len(filler_cycle)]
        for index in range(location_count - len(names))
    )

    # Archipelago's EXCLUDED locations accept filler only. Preserve every
    # route requirement, then replace the least-prioritized useful extras with
    # vigor until every protected check can be filled without an unsafe item.
    excluded_count = sum(
        location.progress_type == LocationProgressType.EXCLUDED
        for location in world.multiworld.get_unfilled_locations(world.player)
    )
    filler_count = sum(
        not ITEM_BY_NAME[name].progression and not ITEM_BY_NAME[name].useful
        for name in names
    )
    replacements_needed = max(0, excluded_count - filler_count)
    for index in range(len(names) - 1, -1, -1):
        if replacements_needed == 0:
            break
        item = ITEM_BY_NAME[names[index]]
        if not item.progression and item.useful:
            names[index] = filler_cycle[index % len(filler_cycle)]
            replacements_needed -= 1
    if replacements_needed:
        raise RuntimeError(
            "Not enough non-progression items to fill protected Lords of the Fallen locations"
        )

    world.multiworld.itempool += [world.create_item(name) for name in names]

    if world.options.shuffle_key_items and world.options.local_key_items:
        world.options.local_items.value.update(
            item.name
            for item in ITEM_BY_NAME.values()
            if item.category == "key" and item.progression
        )

    if world.options.shuffle_key_items and world.options.early_pilgrims_perch_key:
        world.multiworld.local_early_items[world.player]["Pilgrim's Perch Key"] = 1
    if world.options.shuffle_key_items and world.options.early_fief_key:
        world.multiworld.local_early_items[world.player]["Fief Key"] = 1
