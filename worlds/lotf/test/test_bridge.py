from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from ..client.bridge import PROTOCOL_VERSION, GameBridge, decode, encode


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
