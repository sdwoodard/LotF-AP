import asyncio
from types import SimpleNamespace
from unittest import TestCase

from NetUtils import NetworkItem

from ..client.client import LordsOfTheFallenContext
from ..client.bridge import PROTOCOL_VERSION
from ..data import GAME


class _Names:
    @staticmethod
    def lookup_in_game(item_id: int, game: str) -> str:
        return {100: "Pilgrim's Perch Key", 200: "Morph Ball"}[item_id]


class TestClientPresentation(TestCase):
    def test_same_game_item_uses_player_name_and_lotf_icon_path(self) -> None:
        context = SimpleNamespace(
            slot_data={"markers": [{"location": 1, "source": "shop"}]},
            server_locations={1},
            locations_info={1: NetworkItem(100, 1, 2, 0)},
            slot_info={2: SimpleNamespace(game=GAME, name="Alice")},
            player_names={2: "Alice"},
            item_names=_Names(),
            slot=1,
        )
        row = LordsOfTheFallenContext._build_placements(context)[1]
        self.assertEqual("Alice's Pilgrim's Perch Key", row["name"])
        self.assertTrue(row["same_game"])
        self.assertIn("another Lampbearer", row["description"])

    def test_other_game_shop_item_uses_destination_world_description(self) -> None:
        context = SimpleNamespace(
            slot_data={"markers": [{"location": 1, "source": "shop"}]},
            server_locations={1},
            locations_info={1: NetworkItem(200, 1, 2, 0)},
            slot_info={2: SimpleNamespace(game="Super Metroid", name="Samus")},
            player_names={2: "Samus"},
            item_names=_Names(),
            slot=1,
        )
        row = LordsOfTheFallenContext._build_placements(context)[1]
        self.assertEqual("Samus's Morph Ball", row["name"])
        self.assertFalse(row["same_game"])
        self.assertIn("world of Super Metroid", row["description"])

    def test_own_item_keeps_normal_name_and_description(self) -> None:
        context = SimpleNamespace(
            slot_data={"markers": [{"location": 1, "source": "shop"}]},
            server_locations={1},
            locations_info={1: NetworkItem(100, 1, 1, 0)},
            slot_info={1: SimpleNamespace(game=GAME, name="Lampbearer")},
            player_names={1: "Lampbearer"},
            item_names=_Names(),
            slot=1,
        )
        row = LordsOfTheFallenContext._build_placements(context)[1]
        self.assertEqual("Pilgrim's Perch Key", row["name"])
        self.assertEqual("", row["description"])
        self.assertTrue(row["own"])


class _Diagnostic:
    def info(self, *_args, **_kwargs) -> None:
        pass

    def debug(self, *_args, **_kwargs) -> None:
        pass

    def error(self, *_args, **_kwargs) -> None:
        pass


class _Bridge:
    def __init__(self) -> None:
        self.commits = []

    def commit(self, *args) -> None:
        self.commits.append(args)


class TestClientRecoveryState(TestCase):
    def test_room_info_seed_is_retained_for_diagnostics_and_recovery(self) -> None:
        context = object.__new__(LordsOfTheFallenContext)
        context.seed_name = None
        context.on_package("RoomInfo", {"seed_name": "88619253776184603392"})
        self.assertEqual("88619253776184603392", context.room_seed_name())

    def test_pickup_safety_profile_is_explicit(self) -> None:
        context = object.__new__(LordsOfTheFallenContext)
        context.slot_data = {"options": {"shuffle_key_items": 0, "shuffle_quest_items": 0}}
        self.assertIn("world-pickup randomization", context.pickup_safety_profile())
        context.slot_data["options"]["shuffle_quest_items"] = 1
        self.assertIn("experimental", context.pickup_safety_profile())
        self.assertIn("quest items", context.pickup_safety_profile())

    def test_mod_and_apworld_version_mismatch_disables_bridge(self) -> None:
        context = object.__new__(LordsOfTheFallenContext)
        context.slot_data = {"world_version": "0.1.0", "options": {}}
        context.bridge_ready = True
        context.bridge_status = ""
        context.diagnostic = _Diagnostic()
        event = SimpleNamespace(
            verb="HELLO",
            fields=("session", "9.9.9", str(PROTOCOL_VERSION), "boot"),
        )
        asyncio.run(context._handle_bridge_event(event))
        self.assertFalse(context.bridge_ready)
        self.assertIn("Package mismatch", context.bridge_status)

    def test_restore_ack_commits_once_and_enables_normal_delivery_after_commit_ack(self) -> None:
        context = object.__new__(LordsOfTheFallenContext)
        context.session = "session"
        context.diagnostic = _Diagnostic()
        context.bridge = _Bridge()
        context.committed_cursor = 0
        context.sent_item_count = 0
        context.load_synchronized = False
        context.bridge_status = ""
        context.pending_recovery = {
            "id": "recovery",
            "target_cursor": 4,
            "expected": {100},
            "acknowledged": set(),
            "waiting_commit": False,
        }

        context._handle_bridge_ack(("session", "RESTORE", "recovery", "100", "1", "0", "1"))
        self.assertEqual([("session", "recovery", 4)], context.bridge.commits)
        self.assertFalse(context.load_synchronized)

        context._handle_bridge_ack(("session", "COMMIT", "recovery", "4"))
        self.assertTrue(context.load_synchronized)
        self.assertEqual(4, context.sent_item_count)
        self.assertEqual(4, context.committed_cursor)
        self.assertIsNone(context.pending_recovery)
