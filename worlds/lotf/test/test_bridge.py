from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import SkipTest, TestCase

from ..client.bridge import PROTOCOL_VERSION, GameBridge, decode, encode


REPOSITORY_ROOT = Path(__file__).parents[3]


class TestGameBridge(TestCase):
    def test_incomplete_event_is_buffered(self) -> None:
        with TemporaryDirectory() as temporary:
            bridge = GameBridge(Path(temporary))
            bridge.events_path.write_bytes(b"HELLO\tsession")
            self.assertEqual([], bridge.read_events())

            with bridge.events_path.open("ab") as stream:
                stream.write(b"\t0.1.0\nCHECK\tsession\t202310001\n")

            events = bridge.read_events()
            self.assertEqual("HELLO", events[0].verb)
            self.assertEqual(("session", "0.1.0"), events[0].fields)
            self.assertEqual("CHECK", events[1].verb)

    def test_commands_are_ascii_and_percent_encoded(self) -> None:
        with TemporaryDirectory() as temporary:
            bridge = GameBridge(Path(temporary))
            bridge.reset("session", "seed name", "Lamp bearer")
            bridge.ping("session")
            payload = bridge.commands_path.read_bytes()

            payload.decode("ascii")
            self.assertIn(
                f"RESET\t{PROTOCOL_VERSION}\tsession\tseed%20name\tLamp%20bearer\n".encode(),
                payload,
            )
            self.assertTrue(payload.endswith(b"PING\tsession\n"))

    def test_unicode_and_protocol_delimiters_round_trip(self) -> None:
        value = "Lämpbearer's ルーン\tline\n%"
        encoded = encode(value)
        encoded.encode("ascii")
        self.assertNotIn("\t", encoded)
        self.assertNotIn("\n", encoded)
        self.assertEqual(value, decode(encoded))

    def test_configuration_sends_goal_mode_in_options(self) -> None:
        with TemporaryDirectory() as temporary:
            bridge = GameBridge(Path(temporary))
            bridge.reset("session", "seed", "slot")
            bridge.configure(
                "session",
                {"options": {"death_link": 1, "item_delivery_delay": 750, "goal": 1}},
                set(),
            )
            payload = bridge.commands_path.read_text(encoding="ascii")
            self.assertIn("OPTIONS\tsession\t1\t750\t1\n", payload)

    def test_configuration_includes_shop_and_remote_item_presentation(self) -> None:
        with TemporaryDirectory() as temporary:
            bridge = GameBridge(Path(temporary))
            bridge.reset("session", "seed", "slot")
            bridge.configure(
                "session",
                {
                    "markers": [
                        {
                            "location": 123,
                            "marker": "ITM_KEY_Test",
                            "suppress": True,
                            "source": "shop",
                            "guid": "A" * 32,
                            "retail_row": "1_Grove_AX_Easy",
                        }
                    ],
                    "items": {
                        "456": {
                            "asset": "/Game/Test.Test_C",
                            "quantity": 2,
                            "name": "Test Item",
                            "unique": True,
                        }
                    },
                    "options": {},
                },
                set(),
                {
                    123: {
                        "recipient": 2,
                        "player": "Alice",
                        "game": "Another Game",
                        "item": 789,
                        "name": "Alice's Useful Thing",
                        "own": False,
                        "same_game": False,
                        "description": "A wayfaring relic.",
                    }
                },
            )
            payload = bridge.commands_path.read_text(encoding="ascii")
            self.assertIn(
                "MARK\tsession\t123\tITM_KEY_Test\t1\t1\t"
                + "A" * 32
                + "\t1_Grove_AX_Easy\n",
                payload,
            )
            self.assertIn("ITEM\tsession\t456\t/Game/Test.Test_C\t2\tTest%20Item\t1\n", payload)
            self.assertIn(
                "PLACE\tsession\t123\t2\tAlice\tAnother%20Game\t789\tAlice%27s%20Useful%20Thing\t0\t0\tA%20wayfaring%20relic.\n",
                payload,
            )

    def test_reset_does_not_truncate_game_events(self) -> None:
        with TemporaryDirectory() as temporary:
            bridge = GameBridge(Path(temporary))
            bridge.events_path.write_bytes(b"CHECK\told-session\t123\n")
            bridge.reset("new-session", "seed", "slot")
            self.assertEqual(b"CHECK\told-session\t123\n", bridge.events_path.read_bytes())
            self.assertEqual([], bridge.read_events())

            with bridge.events_path.open("ab") as stream:
                stream.write(b"HELLO\tnew-session\t0.1.0\t3\tboot\n")
            events = bridge.read_events()
            self.assertEqual(1, len(events))
            self.assertEqual("HELLO", events[0].verb)


class TestLuaPickupContract(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        bridge_path = REPOSITORY_ROOT / "game-mod" / "LotFArchipelago" / "Scripts" / "bridge.lua"
        if not bridge_path.is_file():
            raise SkipTest("Lua contract checks require the full LotF-AP repository")
        cls.source = bridge_path.read_text(encoding="utf-8")

    def test_loaded_pickups_are_prepared_by_guid(self) -> None:
        self.assertIn('FindAllOf("Pickup")', self.source)
        self.assertIn("Bridge.prepared_items[item_name]", self.source)
        self.assertIn("pickup_identity(pickup)", self.source)
        self.assertIn("B21D92B8406214F0AEAF6B9B239BB661", self.source)

    def test_multiple_observable_pickup_paths_are_registered(self) -> None:
        self.assertIn("Pickup:OnTakePickupEndDelegate", self.source)
        self.assertIn("InteractionComponent:NotifyOnInteractionActivate", self.source)
        self.assertIn("InteractionComponent:OnInteractionActivate", self.source)
        self.assertIn("InventoryComponent:OnItemAdded", self.source)

    def test_reflection_and_protocol_paths_fail_closed(self) -> None:
        self.assertNotIn("value[method](value)", self.source)
        mismatch = self.source.index('if protocol_version ~= Bridge.protocol_version then')
        valid_reset = self.source.index("reset(session)", mismatch)
        self.assertIn("reset(nil)", self.source[mismatch:valid_reset])

    def test_game_online_mode_is_forced_off(self) -> None:
        self.assertIn('FindFirstOf("HexGameUserSettings")', self.source)
        self.assertIn("SetOnlineModeEnabled(false)", self.source)
        self.assertIn("SetCrossplayEnabled(false)", self.source)
        self.assertIn("SetAllowInvasionsEnabled(false)", self.source)
