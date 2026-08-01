import test.bases as ap_test_bases
from collections import Counter
from importlib.resources import files
from BaseClasses import LocationProgressType
from Options import ItemsAccessibility
from worlds.LauncherComponents import components, icon_paths

from ..components import ICON_KEY
from ..data import (
    ALL_BOSSES_GOAL_REQUIREMENTS,
    ALL_BOSSES_GOAL_LOCATIONS,
    ANY_ENDING_GOAL_REQUIREMENTS,
    CHECK_UNLOCK_ITEMS,
    ENDING_LOCKED_LOCATIONS,
    GAME,
    GRINDY_LOCATION_SOURCES,
    ITEM_BY_NAME,
    ITEMS,
    LOCATION_BY_NAME,
    LOCATIONS,
    PICKUP_LOGIC_AUDIT_SHA256,
    QUEST_LOCATION_REQUIREMENTS,
    REGION_CONNECTIONS,
    REGION_PREFIXES,
    WORLD_PICKUP_LOCATIONS,
    location_description,
    location_is_unsafe,
    location_source,
    pickup_logic_audit_digest,
)
from ..options import LordsOfTheFallenAccessibility
from ..pickup_sublevels import PICKUP_SUBLEVELS


class LordsOfTheFallenTestMixin:
    def test_launcher_icon_is_packaged(self) -> None:
        self.assertTrue(files("worlds.lotf").joinpath("assets", "lotf-icon.png").is_file())
        component = next(row for row in components if row.display_name == "Lords of the Fallen Client")
        self.assertEqual(ICON_KEY, component.icon)
        self.assertEqual("ap:worlds.lotf/assets/lotf-icon.png", icon_paths[ICON_KEY])

    def test_item_and_location_ids_are_unique(self) -> None:
        self.assertEqual(len(ITEMS), len(self.world.item_name_to_id))
        self.assertEqual(len(LOCATIONS), len(self.world.location_name_to_id))
        self.assertTrue(set(self.world.item_name_to_id).isdisjoint(self.world.location_name_to_id))

    def test_every_shuffled_unique_item_has_one_vanilla_check_marker(self) -> None:
        for item in (entry for entry in ITEMS if entry.category in {"key", "quest"}):
            marker = (item.asset or "").rsplit("/", 1)[-1]
            matches = [
                location
                for location in LOCATIONS
                if location.marker == marker
                and location.suppress_group == item.category
            ]
            self.assertEqual(1, len(matches), f"{item.name}: {matches}")

    def test_retail_world_pickups_are_complete_and_throwing_stone_is_vanilla(self) -> None:
        self.assertEqual(597, len(WORLD_PICKUP_LOCATIONS))
        self.assertEqual(597, len({entry.guid for entry in WORLD_PICKUP_LOCATIONS}))
        self.assertFalse(any(entry.retail_row == "816_Quest_QST_Quest" for entry in LOCATIONS))
        self.assertTrue(all(entry.guid and entry.source in {"world_pickup", "quest"} for entry in WORLD_PICKUP_LOCATIONS))
        self.assertEqual(
            {entry.guid for entry in WORLD_PICKUP_LOCATIONS},
            set(PICKUP_SUBLEVELS),
        )
        self.assertTrue(all(PICKUP_SUBLEVELS.values()))
        self.assertEqual(
            {"1995C690487653B5B70EDC9F2B27F630"},
            {guid for guid, maps in PICKUP_SUBLEVELS.items() if len(maps) > 1},
        )
        self.assertTrue(all(entry.logic_region for entry in WORLD_PICKUP_LOCATIONS))
        region_names = {name for edge in REGION_CONNECTIONS for name in edge[:2]}
        self.assertTrue(
            {entry.logic_region for entry in WORLD_PICKUP_LOCATIONS}.issubset(region_names)
        )
        self.assertEqual(
            PICKUP_LOGIC_AUDIT_SHA256,
            pickup_logic_audit_digest(WORLD_PICKUP_LOCATIONS),
        )

    def test_only_the_post_boss_cell_pickup_requires_tancreds_key(self) -> None:
        self.assertEqual(
            ["266_PenitentTower_AX_Difficult"],
            [
                entry.retail_row
                for entry in WORLD_PICKUP_LOCATIONS
                if entry.logic_region == "Tower of Penance - Lift and Prison"
            ],
        )

    def test_item_pool_matches_addressed_locations(self) -> None:
        addressed = [location for location in self.multiworld.get_locations(self.player) if location.address]
        self.assertEqual(len(addressed), len(self.multiworld.itempool))

    def test_slot_data_maps_every_enabled_location(self) -> None:
        slot_data = self.world.fill_slot_data()
        addressed = [location for location in self.multiworld.get_locations(self.player) if location.address]
        self.assertEqual(
            len(addressed),
            sum(int(row["location"]) > 0 for row in slot_data["markers"]),
        )
        self.assertTrue(all(row["asset"] for row in slot_data["items"].values()))
        world_pickups = [row for row in slot_data["markers"] if row.get("guid")]
        self.assertEqual(597, len(world_pickups))
        self.assertTrue(
            all(row["location"] > 0 and row["suppress"] and row["retail_row"] for row in world_pickups)
        )

    def test_unsafe_locations_reject_advancement_and_useful_items(self) -> None:
        progression = self.world.create_item("Fief Key")
        useful = self.world.create_item("Deralium Chunk")
        filler = self.world.create_item("Vigor Cache")
        for entry in LOCATIONS:
            if not location_is_unsafe(entry):
                continue
            matches = self.multiworld.get_locations(self.player)
            location = next((row for row in matches if row.name == entry.name), None)
            if location is None:
                continue
            self.assertEqual(LocationProgressType.EXCLUDED, location.progress_type, entry.name)
            self.assertFalse(location.item_rule(progression), entry.name)
            self.assertFalse(location.item_rule(useful), entry.name)
            self.assertTrue(location.item_rule(filler), entry.name)

    def test_no_grindy_sources_are_in_the_pool(self) -> None:
        self.assertFalse(
            [entry.name for entry in LOCATIONS if location_source(entry) in GRINDY_LOCATION_SOURCES]
        )

    def test_advancement_exactly_matches_items_that_unlock_checks(self) -> None:
        self.assertEqual(
            {
                "Pilgrim's Perch Key",
                "Skyrest Bridge Key",
                "Fief Key",
                "Sunless Skein Key",
                "Drainage Control Key",
                "Abbot Vernoff's Key",
                "Monastery Kitchen Key",
                "Tancred's Key",
                "Empyrean Church Key",
                "Royal Key",
                "Rune of Adyr",
                "Flayed Skin",
                "Spurned Progeny Eyeball",
                "Ancient Sentinel Banner",
                "Tattered Sentinel Banner",
            },
            {item.name for item in ITEMS if item.progression},
        )
        self.assertEqual(
            CHECK_UNLOCK_ITEMS,
            {item.name for item in ITEMS if item.progression},
        )
        self.assertEqual(
            {
                "Path of Devotion - Umbral-Tinged Flayed Skin",
                "Upper Calrath - Elegant Perfume",
                "Abbey - Restored Sentinel Banner",
                "Bramis Castle - Empowered Rune of Adyr",
                "Mother's Lull - Withered Rune of Adyr",
            },
            set(QUEST_LOCATION_REQUIREMENTS),
        )

    def test_local_key_option_only_localizes_route_requirements(self) -> None:
        if not (self.world.options.shuffle_key_items and self.world.options.local_key_items):
            return
        self.assertEqual(
            {
                "Pilgrim's Perch Key",
                "Skyrest Bridge Key",
                "Fief Key",
                "Sunless Skein Key",
                "Drainage Control Key",
                "Abbot Vernoff's Key",
                "Monastery Kitchen Key",
                "Tancred's Key",
                "Empyrean Church Key",
                "Royal Key",
            },
            self.world.options.local_items.value,
        )

    def test_all_bosses_excludes_choice_locked_encounters(self) -> None:
        self.assertTrue(set(ALL_BOSSES_GOAL_LOCATIONS).isdisjoint(ENDING_LOCKED_LOCATIONS))
        self.assertIn("Stigma - Unbroken Promise", ALL_BOSSES_GOAL_LOCATIONS)

    def test_goal_requirement_sets_capture_the_full_item_chains(self) -> None:
        self.assertEqual(
            {"Rune of Adyr", "Royal Key"},
            set(ANY_ENDING_GOAL_REQUIREMENTS),
        )
        self.assertEqual(
            {
                "Pilgrim's Perch Key",
                "Fief Key",
                "Drainage Control Key",
                "Monastery Kitchen Key",
                "Abbot Vernoff's Key",
                "Empyrean Church Key",
                "Rune of Adyr",
                "Royal Key",
            },
            set(ALL_BOSSES_GOAL_REQUIREMENTS),
        )

    def test_every_location_has_client_help_text(self) -> None:
        for entry in LOCATIONS:
            self.assertIn(entry.region, REGION_PREFIXES, entry.name)
            self.assertTrue(location_description(entry).strip(), entry.name)

    def test_client_help_text_only_describes_the_check(self) -> None:
        self.assertEqual(
            "Received from Andreas of Ebb at Skyrest Bridge.",
            location_description(LOCATION_BY_NAME["Skyrest - Fief Key"]),
        )
        effect_phrases = (" opens ", " opening ", " used at ", " used for ")
        for entry in LOCATIONS:
            description = f" {location_description(entry).lower()} "
            self.assertFalse(
                any(phrase in description for phrase in effect_phrases),
                f"Item-effect wording in {entry.name}: {description.strip()}",
            )

    def test_accessibility_has_distinct_full_items_and_minimal_modes(self) -> None:
        option_type = self.world.options_dataclass.type_hints["accessibility"]
        self.assertIs(option_type, LordsOfTheFallenAccessibility)
        self.assertTrue(issubclass(option_type, ItemsAccessibility))
        self.assertEqual(
            {0, 1, 2},
            {option_type.from_any(value).value for value in ("full", "items", "minimal")},
        )
        self.assertEqual(option_type.option_full, option_type.default)
        self.assertEqual(option_type.option_full, option_type.from_any(True).value)

    def test_retail_boss_asset_mappings(self) -> None:
        expected = {
            "Congregator of Flesh": "BogLord",
            "Spurned Progeny": "FireGiant",
            "Unbroken Promise": "Fidelitas",
            "Sundered Monarch": "FatherOfMisery",
            "Adyr": "TrueAdyr",
        }
        for boss, asset_label in expected.items():
            location = LOCATION_BY_NAME[f"Stigma - {boss}"]
            self.assertIn(asset_label, location.marker)

        self.assertIn(
            "Fidelitas",
            ITEM_BY_NAME["Remembrance of the Unbroken Promise"].asset,
        )


class TestDefaultOptions(LordsOfTheFallenTestMixin, ap_test_bases.WorldTestBase):
    game = GAME

    def test_requested_release_defaults(self) -> None:
        self.assertTrue(self.world.options.shuffle_key_items)
        self.assertTrue(self.world.options.shuffle_quest_items)
        self.assertFalse(self.world.options.local_key_items)
        self.assertFalse(self.world.options.early_pilgrims_perch_key)
        self.assertFalse(self.world.options.early_fief_key)
        self.assertEqual(30, self.world.options.weapon_upgrade_items.value)
        self.assertEqual(20, self.world.options.sanguinarix_upgrade_items.value)
        self.assertEqual(3, self.world.options.lamp_upgrade_items.value)
        self.assertEqual("full", self.world.options.accessibility.current_key)
        self.assertEqual("off", self.world.options.vigor_skull_smoothing.current_key)
        self.assertEqual("off", self.world.options.weapon_upgrade_smoothing.current_key)

    def test_default_upgrade_pool_matches_vanilla_totals(self) -> None:
        counts = Counter(
            item.name
            for item in self.multiworld.itempool
            if item.player == self.player and item.name in ITEM_BY_NAME
        )
        self.assertEqual(
            {
                "Small Deralium Fragment": 2,
                "Regular Deralium Nugget": 7,
                "Large Deralium Shard": 20,
                "Deralium Chunk": 1,
                "Saintly Quintessence": 20,
                "Antediluvian Chisel": 3,
            },
            {
                name: counts[name]
                for name in (
                    "Small Deralium Fragment",
                    "Regular Deralium Nugget",
                    "Large Deralium Shard",
                    "Deralium Chunk",
                    "Saintly Quintessence",
                    "Antediluvian Chisel",
                )
            },
        )
        self.assertEqual(
            6,
            counts["Small Deralium Fragment"]
            * ITEM_BY_NAME["Small Deralium Fragment"].quantity,
        )
        self.assertEqual(
            7,
            counts["Regular Deralium Nugget"]
            * ITEM_BY_NAME["Regular Deralium Nugget"].quantity,
        )


class TestFullMultiworld(LordsOfTheFallenTestMixin, ap_test_bases.WorldTestBase):
    game = GAME
    options = {
        "goal": "all_bosses",
        "shuffle_key_items": True,
        "shuffle_quest_items": True,
        "include_quest_locations": True,
        "include_world_stigmas": True,
        "missable_location_behavior": "forbid_progression",
        "weapon_upgrade_items": 30,
        "sanguinarix_upgrade_items": 20,
        "lamp_upgrade_items": 3,
    }

    def test_slot_data_requires_exact_safe_boss_set(self) -> None:
        self.assertEqual(
            {
                self.world.location_name_to_id[name]
                for name in ALL_BOSSES_GOAL_LOCATIONS
            },
            set(self.world.fill_slot_data()["goal_locations"]),
        )

    def test_quest_unlock_items_gate_their_checks(self) -> None:
        for location_name, requirements in QUEST_LOCATION_REQUIREMENTS.items():
            state = self.multiworld.get_all_state(False)
            for requirement in requirements:
                state.remove(self.world.create_item(requirement))
            self.assertFalse(
                state.can_reach(location_name, "Location", self.player),
                f"{location_name} is reachable without {sorted(requirements)}",
            )
            for requirement in requirements:
                state.collect(self.world.create_item(requirement))
            self.assertTrue(
                state.can_reach(location_name, "Location", self.player),
                f"{location_name} is not reachable with {sorted(requirements)}",
            )


class TestSmallLocationPool(LordsOfTheFallenTestMixin, ap_test_bases.WorldTestBase):
    game = GAME
    options = {
        "shuffle_key_items": True,
        "shuffle_quest_items": False,
        "include_quest_locations": False,
        "include_world_stigmas": False,
        "missable_location_behavior": "remove",
        "weapon_upgrade_items": 30,
        "sanguinarix_upgrade_items": 20,
        "lamp_upgrade_items": 3,
    }


class TestSuppressionOnlyMarkers(LordsOfTheFallenTestMixin, ap_test_bases.WorldTestBase):
    game = GAME
    options = {
        "shuffle_quest_items": True,
        "missable_location_behavior": "remove",
    }

    def test_removed_quest_checks_still_suppress_vanilla_pickups(self) -> None:
        slot_data = self.world.fill_slot_data()
        self.assertTrue(any(row["location"] == 0 and row["suppress"] for row in slot_data["markers"]))
