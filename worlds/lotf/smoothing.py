"""Post-fill ordering for value-scaled, non-progression item groups."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypeVar

from BaseClasses import CollectionState

from .data import GAME
from .options import ItemSmoothing

if TYPE_CHECKING:
    from BaseClasses import Item, Location, MultiWorld
    from .world import LordsOfTheFallenWorld


VIGOR_SKULL_RANKS: dict[str, int] = {
    "Enervated Vigor Skull": 0,
    "Faint Vigor Skull": 1,
    "Animated Vigor Skull": 2,
    # Archipelago may request its generic filler item during corrections.
    # It grants the same asset tier as an Animated Vigor Skull.
    "Vigor Cache": 2,
    "Seething Vigor Skull": 3,
    "Replete Vigor Skull": 4,
}

WEAPON_UPGRADE_RANKS: dict[str, int] = {
    "Small Deralium Fragment": 0,
    "Regular Deralium Nugget": 1,
    "Large Deralium Shard": 2,
    "Deralium Chunk": 3,
}

# Approximate first-playthrough order. Logical spheres take precedence; this
# order distinguishes locations that share a sphere because no randomized item
# is required between many consecutive base-game areas.
SMOOTHING_REGION_ORDER = (
    "Menu",
    "Defiled Sepulchre",
    "Abandoned Redcopse",
    "Skyrest Bridge",
    "Skyrest Bridge - Locked Crypt",
    "Pilgrim's Perch",
    "Forsaken Fen",
    "Fitzroy's Gorge",
    "Lower Calrath",
    "Lower Calrath - Sunless Skein Annex",
    "Sunless Skein",
    "Cistern",
    "Revelation Depths",
    "Fief of the Chill Curse",
    "Pilgrim's Perch - Belled Rise",
    "Path of Devotion",
    "Manse of the Hallowed Brothers",
    "Manse - Kitchen and Interior",
    "Tower of Penance",
    "Tower of Penance - Lift and Prison",
    "Abbey of the Hallowed Sisters",
    "The Empyrean",
    "The Empyrean - Church",
    "Upper Calrath",
    "Bramis Castle",
    "Bramis Castle - Royal Wing",
    "Rhogar Realm",
    "Mother's Lull",
)
_REGION_RANK = {name: index for index, name in enumerate(SMOOTHING_REGION_ORDER)}

T = TypeVar("T")


def order_for_smoothing(
    values: Sequence[T],
    ranks: Mapping[str, int],
    mode: int,
    random_source,
    *,
    name=lambda value: value.name,
) -> list[T]:
    """Return values in Off, Semi, or Full low-to-high order."""
    ordered = list(values)
    if mode == ItemSmoothing.option_off:
        return ordered
    ordered.sort(key=lambda value: (ranks[name(value)], name(value)))
    if mode == ItemSmoothing.option_semi:
        # Shuffle nearby eighths of the curve. Tier groups remain broadly early
        # or late, while boundaries overlap enough to avoid a rigid staircase.
        band_size = max(3, (len(ordered) + 7) // 8)
        for start in range(0, len(ordered), band_size):
            band = ordered[start : start + band_size]
            random_source.shuffle(band)
            ordered[start : start + band_size] = band
    return ordered


def smoothing_location_sort_key(location: "Location") -> tuple[int, int, int, str, str]:
    if location.game == GAME:
        return (
            0,
            _REGION_RANK.get(location.parent_region.name, len(_REGION_RANK)),
            location.player,
            location.parent_region.name,
            location.name,
        )
    # Other games have no comparable area ordering. Keep their locations
    # deterministic and after known LotF locations within the same sphere.
    return (1, 0, location.player, location.game, location.name)


def apply_item_smoothing(
    multiworld: "MultiWorld", worlds: Sequence["LordsOfTheFallenWorld"]
) -> None:
    """Rearrange owned, unlocked items within their reachable placements."""
    active_worlds = [
        world
        for world in worlds
        if world.options.vigor_skull_smoothing.value != ItemSmoothing.option_off
        or world.options.weapon_upgrade_smoothing.value != ItemSmoothing.option_off
    ]
    if not active_worlds:
        return

    spheres_by_player: dict[int, list[list["Location"]]] = {
        world.player: [] for world in active_worlds
    }
    for sphere in multiworld.get_spheres():
        if not sphere:
            # get_spheres follows this sentinel with locations that are not in
            # logic. Never move a smoothed item into or out of that set.
            break
        for world in active_worlds:
            owned = [
                location
                for location in sphere
                if not location.locked
                and location.item is not None
                and location.item.player == world.player
            ]
            owned.sort(key=smoothing_location_sort_key)
            spheres_by_player[world.player].append(owned)

    state = CollectionState(multiworld)
    for world in active_worlds:
        ordered_locations = [
            location
            for sphere in spheres_by_player[world.player]
            for location in sphere
        ]
        for ranks, mode in (
            (VIGOR_SKULL_RANKS, world.options.vigor_skull_smoothing.value),
            (WEAPON_UPGRADE_RANKS, world.options.weapon_upgrade_smoothing.value),
        ):
            if mode == ItemSmoothing.option_off:
                continue
            locations = [
                location
                for location in ordered_locations
                if location.item is not None and location.item.name in ranks
            ]
            items = order_for_smoothing(
                [location.item for location in locations],
                ranks,
                mode,
                world.random,
            )
            for location, item in zip(locations, items):
                if not location.can_fill(state, item, check_access=False):
                    raise RuntimeError(
                        f"Smoothing cannot place {item} at {location}; "
                        "the original placement rules distinguish items in one smoothing group"
                    )
            for location, item in zip(locations, items):
                location.item = item
                item.location = location
