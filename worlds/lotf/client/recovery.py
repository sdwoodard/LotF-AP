from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


LEDGER_SCHEMA = 1
PRIMARY_SAVE = re.compile(r"^Save(?P<slot>\d{2})\.sav$", re.IGNORECASE)
SAVE_HINT = re.compile(r"Save(?P<slot>\d{2})", re.IGNORECASE)


@dataclass(frozen=True)
class SaveIdentity:
    path: str
    digest: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class RecoveryDecision:
    item_id: int
    baseline: int
    expected: int
    current: int | None
    restore: int
    reason: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SaveTracker:
    """Identify the active primary LotF character save without touching it."""

    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            configured = os.environ.get("LOTF_AP_SAVE_DIR")
            if configured:
                root = Path(configured).expanduser()
            else:
                local_app_data = os.environ.get("LOCALAPPDATA")
                if local_app_data:
                    root = Path(local_app_data) / "LOTF2" / "Saved" / "SaveGames"
                else:
                    roots = (
                        Path.home() / ".local" / "share" / "Steam",
                        Path.home() / ".steam" / "steam",
                    )
                    candidates = [
                        steam
                        / "steamapps"
                        / "compatdata"
                        / "1501750"
                        / "pfx"
                        / "drive_c"
                        / "users"
                        / "steamuser"
                        / "AppData"
                        / "Local"
                        / "LOTF2"
                        / "Saved"
                        / "SaveGames"
                        for steam in roots
                    ]
                    root = next((path for path in candidates if path.is_dir()), candidates[0])
        self.root = root

    def candidates(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(
            (path for path in self.root.iterdir() if path.is_file() and PRIMARY_SAVE.match(path.name)),
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def fingerprint(path: Path) -> SaveIdentity:
        stat = path.stat()
        return SaveIdentity(str(path.resolve()), _sha256(path), stat.st_size, stat.st_mtime_ns)

    def identify(self, hint: str = "", known_digests: Iterable[str] = ()) -> tuple[SaveIdentity | None, str]:
        candidates = self.candidates()
        if not candidates:
            return None, "no primary SaveNN.sav files were found"

        hint_match = SAVE_HINT.search(hint)
        if hint_match:
            wanted = f"Save{hint_match.group('slot')}.sav".lower()
            matches = [path for path in candidates if path.name.lower() == wanted]
            if len(matches) == 1:
                return self.fingerprint(matches[0]), "matched the game-provided save-slot hint"

        known = set(known_digests)
        if known:
            matches = [identity for identity in map(self.fingerprint, candidates) if identity.digest in known]
            if len(matches) == 1:
                return matches[0], "matched one previously recorded save fingerprint"
            if len(matches) > 1:
                return None, "more than one character save matches this session's recovery ledger"

        if len(candidates) == 1:
            return self.fingerprint(candidates[0]), "only one primary character save exists"

        newest_time = max(path.stat().st_mtime_ns for path in candidates)
        newest = [path for path in candidates if newest_time - path.stat().st_mtime_ns <= 2_000_000_000]
        if len(newest) == 1 and time.time_ns() - newest[0].stat().st_mtime_ns <= 30_000_000_000:
            return self.fingerprint(newest[0]), "selected the only character save written in the last 30 seconds"
        return None, "the active character save is ambiguous; no recovery grant will be attempted"


class RecoveryLedger:
    """Atomic save checkpoints and cross-seed bindings for rollback recovery."""

    def __init__(self, root: Path, session: str, room_fingerprint: str, slot_name: str) -> None:
        self.root = root / "recovery"
        self.root.mkdir(parents=True, exist_ok=True)
        self.session = session
        self.room_fingerprint = room_fingerprint
        self.slot_name = slot_name
        self.path = self.root / f"{session}.json"
        self.bindings_path = self.root / "save-bindings.json"
        self.data = self._read_json(
            self.path,
            {
                "schema": LEDGER_SCHEMA,
                "session": session,
                "room_fingerprint": room_fingerprint,
                "slot_name": slot_name,
                "checkpoints": {},
            },
        )
        if (
            self.data.get("schema") != LEDGER_SCHEMA
            or self.data.get("session") != session
            or self.data.get("room_fingerprint") != room_fingerprint
        ):
            raise RuntimeError("Recovery ledger identity or schema does not match this room")

    @staticmethod
    def _read_json(path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Cannot read recovery state {path}: {error}") from error
        if not isinstance(value, dict):
            raise RuntimeError(f"Recovery state {path} is not a JSON object")
        return value

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)

    @property
    def known_digests(self) -> set[str]:
        return set(self.data.get("checkpoints", {}))

    def checkpoint(self, identity: SaveIdentity, cursor: int, counts: Mapping[int, int]) -> None:
        if cursor < 0 or any(item_id < 0 or count < 0 for item_id, count in counts.items()):
            raise ValueError("A recovery checkpoint cannot contain negative values")
        self.data.setdefault("checkpoints", {})[identity.digest] = {
            "path": identity.path,
            "size": identity.size,
            "mtime_ns": identity.mtime_ns,
            "cursor": cursor,
            "counts": {str(item_id): count for item_id, count in sorted(counts.items())},
            "recorded_at": int(time.time()),
        }
        self._write_json(self.path, self.data)

        bindings = self._read_json(self.bindings_path, {"schema": LEDGER_SCHEMA, "saves": {}, "paths": {}})
        if bindings.get("schema") != LEDGER_SCHEMA:
            raise RuntimeError("Save-binding schema is newer than this client")
        binding = {
            "session": self.session,
            "room_fingerprint": self.room_fingerprint,
            "slot_name": self.slot_name,
            "path": identity.path,
            "recorded_at": int(time.time()),
        }
        bindings.setdefault("saves", {})[identity.digest] = binding
        bindings.setdefault("paths", {})[str(Path(identity.path).resolve()).casefold()] = binding
        self._write_json(self.bindings_path, bindings)

    def lookup(self, identity: SaveIdentity) -> dict | None:
        value = self.data.get("checkpoints", {}).get(identity.digest)
        return value if isinstance(value, dict) else None

    def conflict(self, identity: SaveIdentity) -> dict | None:
        bindings = self._read_json(self.bindings_path, {"schema": LEDGER_SCHEMA, "saves": {}, "paths": {}})
        binding = bindings.get("saves", {}).get(identity.digest)
        if not isinstance(binding, dict):
            binding = bindings.get("paths", {}).get(str(Path(identity.path).resolve()).casefold())
        if isinstance(binding, dict) and binding.get("session") != self.session:
            return binding
        return None


def compute_recovery_decisions(
    checkpoint: Mapping[str, object],
    received: Sequence[tuple[int, int]],
    current_counts: Mapping[int, int | None],
) -> list[RecoveryDecision]:
    """Compare one save checkpoint to authoritative received-item history.

    Only items received after the checkpoint cursor are added to its observed
    baseline.  This is what prevents a spent pre-checkpoint consumable from
    being recreated while still restoring stackable items lost to rollback.
    """

    cursor = int(checkpoint.get("cursor", 0))
    if cursor < 0 or cursor > len(received):
        raise ValueError("Checkpoint receive cursor is outside the server item history")
    raw_counts = checkpoint.get("counts", {})
    if not isinstance(raw_counts, Mapping):
        raise ValueError("Checkpoint inventory counts are invalid")
    baseline_counts = {int(item_id): int(count) for item_id, count in raw_counts.items()}
    post_checkpoint = Counter()
    for item_id, quantity in received[cursor:]:
        if quantity <= 0:
            raise ValueError("Received-item quantities must be positive")
        post_checkpoint[item_id] += quantity

    decisions: list[RecoveryDecision] = []
    for item_id, added in sorted(post_checkpoint.items()):
        baseline = baseline_counts.get(item_id, 0)
        expected = baseline + added
        current = current_counts.get(item_id)
        if current is None:
            decisions.append(RecoveryDecision(item_id, baseline, expected, None, 0, "inventory count unavailable"))
            continue
        restore = max(0, expected - current)
        reason = "restore post-checkpoint deficit" if restore else "already present; do not resend"
        decisions.append(RecoveryDecision(item_id, baseline, expected, current, restore, reason))
    return decisions
