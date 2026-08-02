from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

from .diagnostics import default_data_root

PROTOCOL_VERSION = 7
MAX_RECORD_BYTES = 64 * 1024
ROTATE_EVENTS_AT = 16 * 1024 * 1024


def encode(value: object) -> str:
    return quote(str(value), safe="/._-:")


def decode(value: str) -> str:
    return unquote(value)


@dataclass(frozen=True)
class BridgeEvent:
    verb: str
    fields: tuple[str, ...]


class GameBridge:
    """Append-only IPC used by CommonClient and the in-process Lua mod.

    The protocol intentionally uses ASCII line records rather than JSON.  Lua
    5.4 and Python can both recover cleanly after either process exits halfway
    through a write, and no third-party Lua module is required.
    """

    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            root = default_data_root() / "bridge"
        self.root = root
        self.commands_path = root / "commands.txt"
        self.events_path = root / "events.txt"
        self._event_offset = 0
        self._event_partial = b""
        self.root.mkdir(parents=True, exist_ok=True)

    def reset(self, session: str, seed: str, slot: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if self.events_path.exists() and self.events_path.stat().st_size >= ROTATE_EVENTS_AT:
            previous = self.events_path.with_suffix(".previous.txt")
            try:
                os.replace(self.events_path, previous)
            except OSError:
                # The game may have opened the file between stat and replace.
                # Skipping rotation is safer than interrupting configuration.
                pass
        # Ignore stale events, but do not truncate a file while Lua may be in
        # the middle of appending to it. Durable checks are replayed by Lua
        # after READY, so a client restart cannot lose a server update.
        self._event_offset = self.events_path.stat().st_size if self.events_path.exists() else 0
        self._event_partial = b""
        temporary = self.commands_path.with_suffix(".tmp")
        with temporary.open("w", encoding="ascii", newline="") as stream:
            stream.write(self._line("RESET", PROTOCOL_VERSION, session, seed, slot))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.commands_path)

    def append(self, verb: str, *fields: object) -> None:
        with self.commands_path.open("a", encoding="ascii", newline="") as stream:
            stream.write(self._line(verb, *fields))
            stream.flush()

    def configure(
        self,
        session: str,
        slot_data: dict,
        checked_locations: set[int],
        placements: dict[int, dict] | None = None,
    ) -> None:
        for row in slot_data.get("markers", []):
            self.append(
                "MARK",
                session,
                int(row["location"]),
                row["marker"],
                1 if row.get("suppress", False) else 0,
                1 if row.get("source") == "shop" else 0,
                row.get("guid", ""),
                row.get("retail_row", ""),
            )
        for item_id, row in slot_data.get("items", {}).items():
            if row.get("asset"):
                self.append(
                    "ITEM",
                    session,
                    int(item_id),
                    row["asset"],
                    int(row.get("quantity", 1)),
                    row.get("name", f"AP item {item_id}"),
                    1 if row.get("unique", False) else 0,
                )
        for location, row in sorted((placements or {}).items()):
            self.append(
                "PLACE",
                session,
                location,
                int(row["recipient"]),
                row["player"],
                row["game"],
                int(row["item"]),
                row["name"],
                1 if row.get("own", False) else 0,
                1 if row.get("same_game", False) else 0,
                row.get("description", ""),
            )
        for location in sorted(checked_locations):
            self.append("CHECKED", session, location)
        options = slot_data.get("options", {})
        self.append(
            "OPTIONS",
            session,
            int(options.get("death_link", 0)),
            int(options.get("item_delivery_delay", 1000)),
            int(options.get("goal", 0)),
        )
        self.append("READY", session)

    def grant(self, session: str, index: int, item_id: int) -> None:
        self.append("GRANT", session, index, item_id)

    def baseline(self, session: str, recovery_id: str, cursor: int) -> None:
        self.append("BASELINE", session, recovery_id, cursor)

    def audit(self, session: str, request_id: str, reason: str) -> None:
        self.append("AUDIT", session, request_id, reason)

    def restore(
        self,
        session: str,
        recovery_id: str,
        item_id: int,
        quantity: int,
        expected: int,
        current: int,
    ) -> None:
        self.append("RESTORE", session, recovery_id, item_id, quantity, expected, current)

    def commit(self, session: str, recovery_id: str, cursor: int) -> None:
        self.append("COMMIT", session, recovery_id, cursor)

    def kill(self, session: str, event_id: str) -> None:
        self.append("KILL", session, event_id)

    def ping(self, session: str) -> None:
        self.append("PING", session)

    def read_events(self) -> list[BridgeEvent]:
        if not self.events_path.exists():
            return []
        size = self.events_path.stat().st_size
        if size < self._event_offset:
            self._event_offset = 0
            self._event_partial = b""
        with self.events_path.open("rb") as stream:
            stream.seek(self._event_offset)
            payload = stream.read()
            self._event_offset = stream.tell()

        payload = self._event_partial + payload
        if not payload:
            return []
        complete, separator, partial = payload.rpartition(b"\n")
        if not separator:
            if len(payload) > MAX_RECORD_BYTES:
                self._event_partial = b""
                return [BridgeEvent("MALFORMED", ("oversized incomplete event record",))]
            self._event_partial = payload
            return []
        self._event_partial = partial

        events: list[BridgeEvent] = []
        for raw_line in complete.splitlines():
            if len(raw_line) > MAX_RECORD_BYTES:
                events.append(BridgeEvent("MALFORMED", ("oversized event record",)))
                continue
            try:
                parts = raw_line.decode("ascii").split("\t")
                if parts and parts[0]:
                    events.append(BridgeEvent(parts[0], tuple(decode(field) for field in parts[1:])))
            except (UnicodeDecodeError, ValueError):
                # Invalid complete records are ignored; an incomplete trailing
                # record remains buffered until its newline arrives.
                continue
        return events

    @staticmethod
    def _line(verb: str, *fields: object) -> str:
        line = "\t".join((verb, *(encode(field) for field in fields))) + "\n"
        if len(line.encode("ascii")) > MAX_RECORD_BYTES:
            raise ValueError(f"Bridge {verb} record exceeds {MAX_RECORD_BYTES} bytes")
        return line
