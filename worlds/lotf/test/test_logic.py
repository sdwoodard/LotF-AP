from unittest import TestCase

from ..logic import reachable_regions


class TestSharedLogic(TestCase):
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
                "Fief Key",
                "Drainage Control Key",
                "Abbot Vernoff's Key",
                "Rune of Adyr",
            },
            shuffle_key_items=True,
            shuffle_quest_items=True,
        )
        self.assertIn("Fief of the Chill Curse", reached)
        self.assertIn("The Empyrean", reached)
        self.assertIn("Bramis Castle", reached)
        self.assertIn("Mother's Lull", reached)
