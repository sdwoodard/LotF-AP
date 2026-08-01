from unittest import TestCase

from ..data import ITEMS, LOCATIONS
from ..logic import reachable_regions


class TestSharedLogic(TestCase):
    def test_vanilla_progression_checks_are_not_behind_their_own_item(self) -> None:
        progression = {item.name for item in ITEMS if item.progression}
        for item in (entry for entry in ITEMS if entry.progression):
            marker = (item.asset or "").rsplit("/", 1)[-1]
            location = next(
                entry for entry in LOCATIONS if entry.marker == marker
            )
            reached = reachable_regions(
                progression - {item.name},
                shuffle_key_items=True,
                shuffle_quest_items=True,
            )
            self.assertIn(
                location.logic_region or location.region,
                reached,
                f"{item.name} is self-locked at {location.name}",
            )

    def test_vanilla_items_do_not_gate_client_logic(self) -> None:
        reached = reachable_regions(
            set(), shuffle_key_items=False, shuffle_quest_items=False
        )
        self.assertIn("Bramis Castle", reached)
        self.assertIn("Mother's Lull", reached)

    def test_shuffled_items_gate_their_routes(self) -> None:
        reached = reachable_regions(
            set(), shuffle_key_items=True, shuffle_quest_items=True
        )
        self.assertNotIn("Fief of the Chill Curse", reached)
        self.assertNotIn("Abbey of the Hallowed Sisters", reached)
        self.assertNotIn("Revelation Depths", reached)
        self.assertNotIn("Bramis Castle", reached)

        reached = reachable_regions(
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
            },
            shuffle_key_items=True,
            shuffle_quest_items=True,
        )
        self.assertIn("Fief of the Chill Curse", reached)
        self.assertIn("The Empyrean", reached)
        self.assertIn("The Empyrean - Church", reached)
        self.assertIn("Bramis Castle", reached)
        self.assertIn("Bramis Castle - Royal Wing", reached)
        self.assertIn("Mother's Lull", reached)
