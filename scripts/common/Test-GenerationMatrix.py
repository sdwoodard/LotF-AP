#!/usr/bin/env python3
"""Generate and inspect a broad Lords of the Fallen option matrix.

Run this against an Archipelago source checkout with ``lotf.apworld`` installed
in ``custom_worlds``. The default run covers every combination of the ten
finite LotF choice/toggle dimensions and all three accessibility modes exactly
once. Numeric options cycle through minimum, near-minimum, default,
near-maximum, and maximum values.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import sys
import time
from argparse import Namespace
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence


GAME = "Lords of the Fallen"
MIXED_GAME = "ChecksFinder"
GENERATION_STEPS = (
    "generate_early",
    "create_regions",
    "create_items",
    "set_rules",
    "connect_entrances",
    "generate_basic",
    "pre_fill",
)

CORE_DIMENSIONS: tuple[tuple[str, tuple[Any, ...]], ...] = (
    ("accessibility", ("full", "items", "minimal")),
    ("goal", ("any_ending", "all_bosses")),
    ("include_quest_locations", (False, True)),
    ("include_world_stigmas", (False, True)),
    ("shuffle_key_items", (False, True)),
    ("shuffle_quest_items", (False, True)),
    ("local_key_items", (False, True)),
    ("early_pilgrims_perch_key", (False, True)),
    ("early_fief_key", (False, True)),
    ("remembrance_items", (False, True)),
    ("missable_location_behavior", ("forbid_progression", "remove")),
)
CORE_COMBINATION_COUNT = 1
for _name, _values in CORE_DIMENSIONS:
    CORE_COMBINATION_COUNT *= len(_values)

NUMERIC_CYCLES: dict[str, tuple[int, ...]] = {
    "progression_balancing": (0, 1, 50, 98, 99),
    "weapon_upgrade_items": (0, 1, 8, 29, 30),
    "sanguinarix_upgrade_items": (0, 1, 5, 19, 20),
    "lamp_upgrade_items": (0, 1, 2, 3),
    "death_link_amnesty": (1, 2, 5, 9, 10),
    "item_delivery_delay": (250, 251, 1000, 4999, 5000),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archipelago-path", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--solo-cases", type=int, default=256)
    parser.add_argument("--same-game-cases", type=int, default=512)
    parser.add_argument("--same-game-slots", type=int, default=4)
    parser.add_argument("--mixed-cases", type=int, default=384)
    parser.add_argument("--mixed-lotf-slots", type=int, default=2)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--progress-every", type=int, default=25)
    return parser.parse_args()


ARGS = parse_args()
ARCHIPELAGO_PATH = ARGS.archipelago_path.resolve()
if not (ARCHIPELAGO_PATH / "BaseClasses.py").is_file():
    raise SystemExit(f"Not an Archipelago source checkout: {ARCHIPELAGO_PATH}")
sys.path.insert(0, str(ARCHIPELAGO_PATH))
os.environ.setdefault("SKIP_REQUIREMENTS_UPDATE", "1")

# Ignore unrelated optional-world import errors and explicitly validate the two
# selected worlds below.
logging.disable(logging.CRITICAL)
from BaseClasses import CollectionState, LocationProgressType, MultiWorld
from Fill import distribute_items_restrictive
from Options import ItemsAccessibility
from Utils import version_tuple
import worlds
from worlds.AutoWorld import AutoWorldRegister, call_all
from worlds.generic.Rules import locality_rules

logging.disable(logging.NOTSET)

if GAME not in AutoWorldRegister.world_types:
    raise SystemExit(
        f"{GAME} is not installed. Put lotf.apworld in "
        f"{ARCHIPELAGO_PATH / 'custom_worlds'}."
    )
if MIXED_GAME not in AutoWorldRegister.world_types:
    raise SystemExit(f"The bundled {MIXED_GAME} world could not be loaded.")

lotf_module = sys.modules.get("worlds.lotf")
LOTF_WORLD_SOURCE = str(getattr(lotf_module, "__file__", ""))
if ".apworld" not in LOTF_WORLD_SOURCE.lower():
    raise SystemExit(
        "The matrix must exercise the installed lotf.apworld archive, but "
        f"Lords of the Fallen resolved from {LOTF_WORLD_SOURCE or 'an unknown source'}. "
        "Use an Archipelago checkout without a loose worlds/lotf directory."
    )
_normalized_world_source = LOTF_WORLD_SOURCE.replace("\\", "/")
_custom_world_marker = "/custom_worlds/"
LOTF_WORLD_SOURCE_REPORT = (
    "custom_worlds/" + _normalized_world_source.split(_custom_world_marker, 1)[1]
    if _custom_world_marker in _normalized_world_source
    else _normalized_world_source
)

from worlds.lotf.data import (
    ALL_BOSSES_GOAL_LOCATIONS,
    GRINDY_LOCATION_SOURCES,
    ITEM_BY_NAME,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    LOCATIONS,
    REGION_CONNECTIONS,
    location_is_unsafe,
    location_source,
)
from worlds.lotf.locations import enabled_locations
from worlds.lotf.logic import reachable_regions, requirement_is_active
from worlds.lotf.options import Goal


class MatrixFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixFailure(message)


def option_config(index: int) -> dict[str, Any]:
    """Return one mixed-radix core combination plus numeric boundary values."""
    config: dict[str, Any] = {}
    quotient = index % CORE_COMBINATION_COUNT
    for name, values in CORE_DIMENSIONS:
        config[name] = values[quotient % len(values)]
        quotient //= len(values)

    strides = (1, 3, 7, 11, 13, 17)
    for (name, values), stride in zip(NUMERIC_CYCLES.items(), strides):
        config[name] = values[(index * stride + index // len(values)) % len(values)]
    config["death_link"] = "any_death" if index % 2 else "off"
    return config


def setup_multiworld(
    world_types: Sequence[type], option_rows: Sequence[dict[str, Any]], seed: int
) -> MultiWorld:
    require(len(world_types) == len(option_rows), "World/options count mismatch")
    multiworld = MultiWorld(len(world_types))
    multiworld.game = {
        player: world_type.game for player, world_type in enumerate(world_types, 1)
    }
    multiworld.player_name = {
        player: f"Matrix{seed}_{player}" for player in multiworld.player_ids
    }
    multiworld.set_seed(seed)
    multiworld.seed_name = f"LotFMatrix{seed}"

    namespace = Namespace()
    for player, (world_type, overrides) in enumerate(zip(world_types, option_rows), 1):
        for name, option_type in world_type.options_dataclass.type_hints.items():
            player_values = getattr(namespace, name, {})
            player_values[player] = option_type.from_any(
                overrides.get(name, option_type.default)
            )
            setattr(namespace, name, player_values)
    multiworld.set_options(namespace)
    multiworld.state = CollectionState(multiworld)
    for step in GENERATION_STEPS:
        call_all(multiworld, step)
        if step == "set_rules" and multiworld.players > 1:
            # Main.py applies locality after every world has finished setting
            # item rules and before the remaining generation hooks.
            locality_rules(multiworld)
    distribute_items_restrictive(multiworld)
    call_all(multiworld, "post_fill")
    call_all(multiworld, "finalize_multiworld")
    return multiworld


def expected_item_pool(world: Any) -> list[str]:
    names: list[str] = []
    if world.options.shuffle_key_items:
        names.extend(item.name for item in ITEM_BY_NAME.values() if item.category == "key")
    if world.options.shuffle_quest_items:
        names.extend(item.name for item in ITEM_BY_NAME.values() if item.category == "quest")
    if world.options.remembrance_items:
        names.extend(
            item.name for item in ITEM_BY_NAME.values() if item.category == "remembrance"
        )

    upgrade_cycle = (
        "Small Deralium Fragment",
        "Regular Deralium Nugget",
        "Large Deralium Shard",
        "Deralium Chunk",
    )
    names.extend(
        upgrade_cycle[index % len(upgrade_cycle)]
        for index in range(world.options.weapon_upgrade_items.value)
    )
    names.extend(
        "Saintly Quintessence"
        for _ in range(world.options.sanguinarix_upgrade_items.value)
    )
    names.extend(
        "Antediluvian Chisel" for _ in range(world.options.lamp_upgrade_items.value)
    )

    addressed_locations = [
        location
        for location in world.multiworld.get_locations(world.player)
        if location.address is not None
    ]
    location_count = len(addressed_locations)
    if len(names) > location_count:
        progression_names = {
            item.name for item in ITEM_BY_NAME.values() if item.progression
        }
        required = [name for name in names if name in progression_names]
        optional = [name for name in names if name not in progression_names]
        names = (required + optional)[:location_count]
    names.extend("Vigor Cache" for _ in range(location_count - len(names)))

    excluded_count = sum(
        location.progress_type == LocationProgressType.EXCLUDED
        for location in addressed_locations
    )
    filler_count = sum(
        not ITEM_BY_NAME[name].progression and not ITEM_BY_NAME[name].useful
        for name in names
    )
    replacements = max(0, excluded_count - filler_count)
    for index in range(len(names) - 1, -1, -1):
        if not replacements:
            break
        item = ITEM_BY_NAME[names[index]]
        if not item.progression and item.useful:
            names[index] = "Vigor Cache"
            replacements -= 1
    require(not replacements, "Expected pool could not supply protected locations")
    return names


class Coverage:
    def __init__(self) -> None:
        self.values: dict[str, set[Any]] = defaultdict(set)
        self.generated_worlds = 0
        self.lotf_slots = 0
        self.spheres = 0
        self.cross_game_items = 0
        self.cross_lotf_items = 0
        self.nonlocal_keys = 0
        self.actual_counts: dict[str, set[int]] = defaultdict(set)

    def record_options(self, config: dict[str, Any]) -> None:
        for name, value in config.items():
            self.values[name].add(value)


COVERAGE = Coverage()


def audit_lotf_player(multiworld: MultiWorld, player: int, config: dict[str, Any]) -> None:
    world = multiworld.worlds[player]
    COVERAGE.lotf_slots += 1
    COVERAGE.record_options(config)

    require(
        world.options_dataclass.type_hints["accessibility"] is ItemsAccessibility,
        "LotF accessibility is not the distinct full/items/minimal option type",
    )
    require(
        world.options.accessibility.current_key == config["accessibility"],
        f"Accessibility parsed as {world.options.accessibility.current_key!r}, "
        f"requested {config['accessibility']!r}",
    )

    expected_locations = {entry.name for entry in enabled_locations(world)}
    actual_locations = {
        location.name
        for location in multiworld.get_locations(player)
        if location.address is not None
    }
    require(
        actual_locations == expected_locations,
        f"Enabled location mismatch for player {player}: "
        f"missing={sorted(expected_locations - actual_locations)}, "
        f"extra={sorted(actual_locations - expected_locations)}",
    )

    expected_names = Counter(expected_item_pool(world))
    actual_names = Counter(
        item.name
        for item in multiworld.itempool
        if item.player == player and item.code in ITEM_NAME_TO_ID.values()
    )
    require(
        actual_names == expected_names,
        f"Item pool mismatch for player {player}: expected={expected_names}, actual={actual_names}",
    )
    for item_name in (
        "Small Deralium Fragment",
        "Regular Deralium Nugget",
        "Large Deralium Shard",
        "Deralium Chunk",
        "Saintly Quintessence",
        "Antediluvian Chisel",
    ):
        COVERAGE.actual_counts[item_name].add(actual_names[item_name])

    active_progression = {
        item.name
        for item in ITEM_BY_NAME.values()
        if item.progression
        and (
            (item.category == "key" and world.options.shuffle_key_items)
            or (item.category == "quest" and world.options.shuffle_quest_items)
        )
    }
    actual_progression = {
        name for name, count in actual_names.items() if count and ITEM_BY_NAME[name].progression
    }
    require(
        actual_progression == active_progression,
        f"Progression activation mismatch for player {player}: "
        f"expected={active_progression}, actual={actual_progression}",
    )

    early_items = multiworld.local_early_items[player]
    for name, enabled in (
        (
            "Pilgrim's Perch Key",
            bool(world.options.shuffle_key_items and world.options.early_pilgrims_perch_key),
        ),
        ("Fief Key", bool(world.options.shuffle_key_items and world.options.early_fief_key)),
    ):
        require(
            early_items.get(name, 0) == int(enabled),
            f"Early-item effect mismatch for {name}, player {player}",
        )

    entry_by_name = {entry.name: entry for entry in LOCATIONS}
    for location in multiworld.get_locations(player):
        if location.address is None:
            continue
        entry = entry_by_name[location.name]
        if location_is_unsafe(entry):
            require(
                location.progress_type == LocationProgressType.EXCLUDED,
                f"Unsafe location is not excluded: {location}",
            )
            require(
                location.item is not None
                and not location.item.advancement
                and not location.item.useful,
                f"Unsafe location received non-filler item: {location} -> {location.item}",
            )
        require(
            location_source(entry) not in GRINDY_LOCATION_SOURCES,
            f"Grindy location source entered pool: {location}",
        )

    slot_data = world.fill_slot_data()
    marker_locations = {
        int(row["location"]) for row in slot_data["markers"] if int(row["location"]) > 0
    }
    require(
        marker_locations == {LOCATION_NAME_TO_ID[name] for name in expected_locations},
        f"Slot marker mismatch for player {player}",
    )
    for row in slot_data["markers"]:
        description = f" {row['description'].lower()} "
        require(
            not any(
                phrase in description
                for phrase in (" opens ", " opening ", " used at ", " used for ")
            ),
            f"Marker description explains the vanilla item effect: {row}",
        )
        if row["unsafe"] and row["location"]:
            location_name = next(
                name for name, code in LOCATION_NAME_TO_ID.items() if code == row["location"]
            )
            require(
                multiworld.get_location(location_name, player).progress_type
                == LocationProgressType.EXCLUDED,
                f"Unsafe marker is not protected: {row}",
            )

    expected_goal_ids = (
        {LOCATION_NAME_TO_ID[name] for name in ALL_BOSSES_GOAL_LOCATIONS}
        if world.options.goal == Goal.option_all_bosses
        else set()
    )
    require(
        set(slot_data["goal_locations"]) == expected_goal_ids,
        f"Goal marker mismatch for player {player}",
    )
    for name in (
        "goal",
        "shuffle_key_items",
        "shuffle_quest_items",
        "death_link",
        "death_link_amnesty",
        "item_delivery_delay",
    ):
        require(
            slot_data["options"][name] == getattr(world.options, name).value,
            f"Slot option {name} mismatch for player {player}",
        )

    if world.options.shuffle_key_items and world.options.local_key_items:
        for item in multiworld.itempool:
            if (
                item.player == player
                and ITEM_BY_NAME[item.name].category == "key"
                and ITEM_BY_NAME[item.name].progression
            ):
                require(
                    item.location is not None and item.location.player == player,
                    f"Local traversal key left player {player}'s world: {item}",
                )
    elif world.options.shuffle_key_items:
        COVERAGE.nonlocal_keys += sum(
            item.player == player
            and ITEM_BY_NAME[item.name].category == "key"
            and ITEM_BY_NAME[item.name].progression
            and item.location is not None
            and item.location.player != player
            for item in multiworld.itempool
        )


def audit_gate_rules(multiworld: MultiWorld, player: int) -> None:
    world = multiworld.worlds[player]
    shuffle_keys = bool(world.options.shuffle_key_items)
    shuffle_quests = bool(world.options.shuffle_quest_items)
    for source, target, requirement in REGION_CONNECTIONS:
        if not requirement_is_active(
            requirement,
            shuffle_key_items=shuffle_keys,
            shuffle_quest_items=shuffle_quests,
        ):
            continue
        state = CollectionState(multiworld)
        for item in ITEM_BY_NAME.values():
            if not item.progression or item.name == requirement:
                continue
            if (item.category == "key" and shuffle_keys) or (
                item.category == "quest" and shuffle_quests
            ):
                state.collect(world.create_item(item.name), True)
        require(
            world.get_region(source).can_reach(state),
            f"Cannot reach source {source} while independently testing {requirement}",
        )
        require(
            not world.get_region(target).can_reach(state),
            f"Gate {source} -> {target} is reachable without {requirement}",
        )
        state.collect(world.create_item(requirement), True)
        require(
            world.get_region(target).can_reach(state),
            f"Gate {source} -> {target} did not open with {requirement}",
        )


def audit_spheres(multiworld: MultiWorld, lotf_players: Iterable[int]) -> int:
    lotf_players = tuple(lotf_players)
    state = CollectionState(multiworld)
    remaining = set(multiworld.get_filled_locations())
    item_sphere: dict[tuple[int, str], int] = {}
    target_sphere: dict[tuple[int, str], int] = {}
    victory_sphere: dict[int, int] = {}
    sphere_index = 0

    while remaining:
        for player in lotf_players:
            world = multiworld.worlds[player]
            for _source, target, requirement in REGION_CONNECTIONS:
                if requirement and world.get_region(target).can_reach(state):
                    target_sphere.setdefault((player, target), sphere_index)

        sphere = {location for location in remaining if location.can_reach(state)}
        if not sphere:
            break

        for player in lotf_players:
            world = multiworld.worlds[player]
            received = {
                item.name
                for item in ITEM_BY_NAME.values()
                if item.progression and state.has(item.name, player)
            }
            shared_regions = reachable_regions(
                received,
                shuffle_key_items=bool(world.options.shuffle_key_items),
                shuffle_quest_items=bool(world.options.shuffle_quest_items),
            )
            for location in sphere:
                if location.player == player:
                    require(
                        location.parent_region.name in shared_regions,
                        f"AP/shared logic disagreement before sphere {sphere_index}: {location}",
                    )

        for location in sphere:
            if location.name == "Victory" and location.player in lotf_players:
                victory_sphere[location.player] = sphere_index
            if location.item and location.item.player in lotf_players:
                item_data = ITEM_BY_NAME.get(location.item.name)
                if item_data and item_data.progression:
                    item_sphere.setdefault(
                        (location.item.player, location.item.name), sphere_index
                    )
            if location.item:
                state.collect(location.item, True, location)
        remaining -= sphere
        sphere_index += 1

    for player in lotf_players:
        world = multiworld.worlds[player]
        for _source, target, requirement in REGION_CONNECTIONS:
            if requirement and world.get_region(target).can_reach(state):
                target_sphere.setdefault((player, target), sphere_index)

        require(
            multiworld.completion_condition[player](state),
            f"LotF player {player} is not complete after reachable spheres",
        )
        accessibility = world.options.accessibility.current_key
        if accessibility == "full":
            require(
                not [location for location in remaining if location.player == player],
                f"Full accessibility left player {player} locations unreachable",
            )
        elif accessibility == "items":
            require(
                not [
                    location
                    for location in remaining
                    if location.item
                    and location.item.player == player
                    and location.item.advancement
                ],
                f"Items accessibility left player {player} progression unreachable",
            )

        shuffle_keys = bool(world.options.shuffle_key_items)
        shuffle_quests = bool(world.options.shuffle_quest_items)
        required_for_goal: set[str] = set()
        if world.options.goal == Goal.option_all_bosses:
            required_for_goal.update(
                requirement
                for _source, _target, requirement in REGION_CONNECTIONS
                if requirement_is_active(
                    requirement,
                    shuffle_key_items=shuffle_keys,
                    shuffle_quest_items=shuffle_quests,
                )
            )
        elif shuffle_quests:
            required_for_goal.add("Rune of Adyr")

        require(player in victory_sphere, f"No reachable Victory event for player {player}")
        for name in required_for_goal:
            require(
                (player, name) in item_sphere,
                f"Goal-required item {name} was never reached for player {player}",
            )
            require(
                item_sphere[(player, name)] < victory_sphere[player],
                f"Victory preceded goal-required {name} for player {player}",
            )

        for source, target, requirement in REGION_CONNECTIONS:
            if not requirement_is_active(
                requirement,
                shuffle_key_items=shuffle_keys,
                shuffle_quest_items=shuffle_quests,
            ):
                continue
            if (player, requirement) not in item_sphere or (player, target) not in target_sphere:
                # Minimal accessibility may strand a branch irrelevant to goal.
                continue
            require(
                target_sphere[(player, target)] > item_sphere[(player, requirement)],
                f"{target} preceded {requirement}; source={source}",
            )

    require(
        multiworld.has_beaten_game(state),
        "Multiworld is not beatable after all reachable progression spheres",
    )
    return sphere_index


def audit_cross_world_placements(multiworld: MultiWorld) -> None:
    for item in multiworld.itempool:
        if item.location is None or item.location.player == item.player:
            continue
        if item.game == GAME and item.location.game == GAME:
            COVERAGE.cross_lotf_items += 1
        if item.game != item.location.game:
            COVERAGE.cross_game_items += 1


def run_case(
    mode: str,
    case_number: int,
    config_indices: Sequence[int],
    include_mixed_game: bool,
) -> None:
    lotf_type = AutoWorldRegister.world_types[GAME]
    world_types = [lotf_type] * len(config_indices)
    option_rows = [option_config(index) for index in config_indices]
    if include_mixed_game:
        world_types.append(AutoWorldRegister.world_types[MIXED_GAME])
        option_rows.append({})

    seed = ARGS.seed + COVERAGE.generated_worlds
    try:
        multiworld = setup_multiworld(world_types, option_rows, seed)
        lotf_players = tuple(range(1, len(config_indices) + 1))
        for player, config in zip(lotf_players, option_rows):
            audit_lotf_player(multiworld, player, config)
            audit_gate_rules(multiworld, player)
        COVERAGE.spheres += audit_spheres(multiworld, lotf_players)
        audit_cross_world_placements(multiworld)
    except Exception as error:
        raise MatrixFailure(
            f"{mode} case {case_number}, seed {seed}, config indices "
            f"{list(config_indices)} failed: {error}"
        ) from error
    finally:
        if "multiworld" in locals():
            del multiworld
        gc.collect()
    COVERAGE.generated_worlds += 1
    if ARGS.progress_every and COVERAGE.generated_worlds % ARGS.progress_every == 0:
        print(
            f"Validated {COVERAGE.generated_worlds} generated multiworlds / "
            f"{COVERAGE.lotf_slots} LotF slots",
            flush=True,
        )


def assert_coverage(total_configurations: int) -> None:
    if total_configurations >= CORE_COMBINATION_COUNT:
        for name, expected_values in CORE_DIMENSIONS:
            require(
                COVERAGE.values[name] == set(expected_values),
                f"Incomplete value coverage for {name}: {COVERAGE.values[name]}",
            )
    for name, expected_values in NUMERIC_CYCLES.items():
        require(
            COVERAGE.values[name] == set(expected_values),
            f"Incomplete numeric boundary coverage for {name}: {COVERAGE.values[name]}",
        )
    require(
        COVERAGE.values["death_link"] == {"off", "any_death"},
        f"Incomplete DeathLink coverage: {COVERAGE.values['death_link']}",
    )
    if ARGS.same_game_cases:
        require(COVERAGE.cross_lotf_items > 0, "No LotF cross-player placement occurred")
    if ARGS.mixed_cases:
        require(COVERAGE.cross_game_items > 0, "No cross-game placement occurred")
        require(
            COVERAGE.nonlocal_keys > 0,
            "No key crossed worlds while local_key_items was disabled",
        )
    for item_name, observed in COVERAGE.actual_counts.items():
        require(
            len(observed) > 1,
            f"Generated count never changed for {item_name}: {observed}",
        )


def serializable_values() -> dict[str, list[Any]]:
    return {
        name: sorted(values, key=lambda value: (str(type(value)), str(value)))
        for name, values in sorted(COVERAGE.values.items())
    }


def main() -> None:
    require(ARGS.same_game_slots > 0, "--same-game-slots must be positive")
    require(ARGS.mixed_lotf_slots > 0, "--mixed-lotf-slots must be positive")
    total_configurations = (
        ARGS.solo_cases
        + ARGS.same_game_cases * ARGS.same_game_slots
        + ARGS.mixed_cases * ARGS.mixed_lotf_slots
    )
    started = time.perf_counter()
    cursor = 0

    for case in range(ARGS.solo_cases):
        run_case("solo", case + 1, (cursor,), False)
        cursor += 1
    for case in range(ARGS.same_game_cases):
        indices = tuple(range(cursor, cursor + ARGS.same_game_slots))
        run_case("lotf_only", case + 1, indices, False)
        cursor += ARGS.same_game_slots
    for case in range(ARGS.mixed_cases):
        indices = tuple(range(cursor, cursor + ARGS.mixed_lotf_slots))
        run_case("mixed", case + 1, indices, True)
        cursor += ARGS.mixed_lotf_slots

    assert_coverage(total_configurations)
    elapsed = time.perf_counter() - started
    report = {
        "result": "passed",
        "archipelago_version": ".".join(str(part) for part in version_tuple),
        "lotf_world_source": LOTF_WORLD_SOURCE_REPORT,
        "seed_start": ARGS.seed,
        "generated_multiworlds": COVERAGE.generated_worlds,
        "lotf_slots": COVERAGE.lotf_slots,
        "core_combinations_available": CORE_COMBINATION_COUNT,
        "core_configurations_tested": total_configurations,
        "logical_spheres": COVERAGE.spheres,
        "lotf_cross_player_items": COVERAGE.cross_lotf_items,
        "cross_game_items": COVERAGE.cross_game_items,
        "nonlocal_keys": COVERAGE.nonlocal_keys,
        "option_values": serializable_values(),
        "observed_generated_item_counts": {
            name: sorted(values) for name, values in sorted(COVERAGE.actual_counts.items())
        },
        "elapsed_seconds": round(elapsed, 3),
    }
    if ARGS.report:
        report_path = ARGS.report.resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
