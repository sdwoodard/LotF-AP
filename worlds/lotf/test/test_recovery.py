from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from ..client.recovery import (
    RecoveryLedger,
    SaveIdentity,
    SaveTracker,
    compute_recovery_decisions,
)


class TestRecoveryMath(TestCase):
    def test_only_post_checkpoint_receipts_are_restored(self) -> None:
        checkpoint = {"cursor": 2, "counts": {"10": 1, "20": 5}}
        received = [(10, 1), (20, 2), (10, 1), (20, 2)]
        decisions = {row.item_id: row for row in compute_recovery_decisions(checkpoint, received, {10: 1, 20: 5})}
        self.assertEqual(1, decisions[10].restore)
        self.assertEqual(2, decisions[20].restore)

    def test_spent_pre_checkpoint_stack_is_not_recreated(self) -> None:
        checkpoint = {"cursor": 1, "counts": {"20": 2}}
        received = [(20, 3)]
        decision = compute_recovery_decisions(checkpoint, received, {20: 0})
        self.assertEqual([], decision)

    def test_existing_unique_or_stack_prevents_duplicate(self) -> None:
        checkpoint = {"cursor": 0, "counts": {"10": 0, "20": 4}}
        received = [(10, 1), (20, 2)]
        decisions = {row.item_id: row for row in compute_recovery_decisions(checkpoint, received, {10: 1, 20: 6})}
        self.assertEqual(0, decisions[10].restore)
        self.assertEqual(0, decisions[20].restore)

    def test_missing_inventory_measurement_never_grants(self) -> None:
        checkpoint = {"cursor": 0, "counts": {"10": 0}}
        decision = compute_recovery_decisions(checkpoint, [(10, 1)], {10: None})[0]
        self.assertEqual(0, decision.restore)
        self.assertEqual("inventory count unavailable", decision.reason)


class TestRecoveryLedger(TestCase):
    def test_checkpoint_is_atomic_and_detects_cross_seed_binding(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = SaveIdentity(str(root / "Save00.sav"), "a" * 64, 100, 200)
            first = RecoveryLedger(root, "session-a", "room-a", "Alice")
            first.checkpoint(identity, 3, {10: 1, 20: 4})
            self.assertEqual(3, first.lookup(identity)["cursor"])
            self.assertFalse(first.path.with_suffix(".json.tmp").exists())

            second = RecoveryLedger(root, "session-b", "room-b", "Bob")
            conflict = second.conflict(identity)
            self.assertIsNotNone(conflict)
            self.assertEqual("session-a", conflict["session"])

            changed = SaveIdentity(identity.path, "b" * 64, 101, 201)
            path_conflict = second.conflict(changed)
            self.assertIsNotNone(path_conflict)
            self.assertEqual("session-a", path_conflict["session"])

    def test_save_tracker_ignores_general_and_backup_saves(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "GeneralSave.sav").write_bytes(b"general")
            (root / "Save00_b1.sav").write_bytes(b"backup")
            (root / "Save00.sav").write_bytes(b"primary")
            tracker = SaveTracker(root)
            identity, reason = tracker.identify()
            self.assertIsNotNone(identity)
            self.assertTrue(identity.path.endswith("Save00.sav"))
            self.assertIn("only one", reason)
