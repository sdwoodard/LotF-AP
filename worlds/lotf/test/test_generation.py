import test.bases as ap_test_bases
from pathlib import Path
from BaseClasses import LocationProgressType
from Options import ItemsAccessibility
from worlds.LauncherComponents import components, icon_paths

from ..components import ICON_KEY
from ..data import (
    ALL_BOSSES_GOAL_LOCATIONS,
    ENDING_LOCKED_LOCATIONS,
    GAME,
    GRINDY_LOCATION_SOURCES,
    ITEM_BY_NAME,
    ITEMS,
    LOCATION_BY_NAME,
    LOCATIONS,
    REGION_PREFIXES,
    location_description,
    location_is_unsafe,
    location_source,
)


class LordsOfTheFallenTestMixin:
    def test_launcher_icon_is_packaged(self) -> None:
        self.assertTrue((Path(__file__).parents[1] / "assets" / "lotf-icon.png").is_file())
        component = next(row for row in components if row.display_name == "Lords of the Fallen Client")
        self.assertEqual(ICON_KEY, component.icon)
        self.assertEqual("ap:worlds.lotf/assets/lotf-icon.png", icon_paths[ICON_KEY])

    def test_item_and_location_ids_are_unique(self) -> None:
        self.assertEqual(len(ITEMS), len(self.world.item_name_to_id))
        self.assertEqual(len(LOCATIONS), len(self.world.location_name_to_id))
        self.assertTrue(set(self.world.item_name_to_id).isdisjoint(self.world.location_name_to_id))

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

    def test_only_route_requirements_are_advancement(self) -> None:
        self.assertEqual(
            {
                "Pilgrim's Perch Key",
                "Fief Key",
                "Drainage Control Key",
                "Abbot Vernoff's Key",
                "Rune of Adyr",
            },
            {item.name for item in ITEMS if item.progression},
        )

    def test_local_key_option_only_localizes_route_requirements(self) -> None:
        if not (self.world.options.shuffle_key_items and self.world.options.local_key_items):
            return
        self.assertEqual(
            {
                "Pilgrim's Perch Key",
                "Fief Key",
                "Drainage Control Key",
                "Abbot Vernoff's Key",
            },
            self.world.options.local_items.value,
        )

    def test_all_bosses_excludes_choice_locked_encounters(self) -> None:
        self.assertTrue(set(ALL_BOSSES_GOAL_LOCATIONS).isdisjoint(ENDING_LOCKED_LOCATIONS))
        self.assertIn("Stigma - Unbroken Promise", ALL_BOSSES_GOAL_LOCATIONS)

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
        self.assertIs(option_type, ItemsAccessibility)
        self.assertEqual(
            {0, 1, 2},
            {option_type.from_any(value).value for value in ("full", "items", "minimal")},
        )

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
