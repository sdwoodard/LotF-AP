from __future__ import annotations

import asyncio
import hashlib
import json
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from CommonClient import ClientCommandProcessor, CommonContext, logger, server_loop
from NetUtils import ClientStatus
from Utils import gui_enabled

from ..data import (
    GAME,
    ITEM_NAME_TO_ID,
    LOCATION_NAME_TO_ID,
    LOCATIONS,
    REGION_PREFIXES,
    location_description,
)
from ..logic import reachable_regions
from ..options import Goal
from .bridge import GameBridge
from .diagnostics import close_diagnostic_logger, create_diagnostic_logger
from .recovery import RecoveryLedger, SaveIdentity, SaveTracker, compute_recovery_decisions


ITEM_ID_TO_NAME = {item_id: name for name, item_id in ITEM_NAME_TO_ID.items()}


class LotFCommandProcessor(ClientCommandProcessor):
    ctx: "LordsOfTheFallenContext"

    def _cmd_bridge(self) -> None:
        """Show the UE4SS game bridge status."""
        logger.info(self.ctx.bridge_status)
        logger.info("Pickup safety profile: %s", self.ctx.pickup_safety_profile())

    def _cmd_resync(self) -> None:
        """Rebuild bridge configuration and re-audit the loaded save."""
        self.ctx.resync_requested = True
        logger.info("Game bridge resync requested.")

    def _cmd_logic(self) -> None:
        """List unchecked Lords of the Fallen checks currently in logic."""
        rows = self.ctx.locations_in_logic()
        if rows is None:
            logger.info("Connect this client to an Archipelago room before using /logic.")
            return
        if not rows:
            logger.info("No unchecked Lords of the Fallen checks are currently in logic.")
            return
        logger.info("Unchecked Lords of the Fallen checks currently in logic (%d):", len(rows))
        for entry in rows:
            prefix = REGION_PREFIXES.get(entry.region, "??")
            logger.info("[%s] %s — %s", prefix, entry.name, location_description(entry))

    def _cmd_inlogic(self) -> None:
        """Alias for /logic."""
        self._cmd_logic()

    def _cmd_diagnostics(self) -> None:
        """Show and update the persistent diagnostic log used for support."""
        self.ctx.write_diagnostic_summary("command")
        logger.info("LotF diagnostic log: %s", self.ctx.diagnostic_log_path)
        logger.info(
            "Include this log, the generated .zip/.archipelago output, your player YAML, and a description of the problem when requesting help."
        )

    def _cmd_save_slot(self, slot: str = "") -> None:
        """Select SaveNN.sav when automatic active-save detection is ambiguous."""
        try:
            number = int(slot)
        except ValueError:
            logger.info("Usage: /save_slot <0-99>")
            return
        if number < 0 or number > 99:
            logger.info("Save slot must be between 0 and 99.")
            return
        self.ctx.forced_save_hint = f"Save{number:02}.sav"
        logger.info("Recovery save selection set to %s; requesting a bridge resync.", self.ctx.forced_save_hint)
        self.ctx.resync_requested = True


class LordsOfTheFallenContext(CommonContext):
    game = GAME
    items_handling = 0b111
    command_processor = LotFCommandProcessor

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.bridge = GameBridge()
        data_root = self.bridge.root.parent
        self.diagnostic, self.diagnostic_log_path, self.client_run_id = create_diagnostic_logger(data_root)
        self.save_tracker = SaveTracker()
        self.recovery_ledger: RecoveryLedger | None = None
        self.bridge_status = "Waiting for an Archipelago room."
        self.slot_data: dict[str, Any] = {}
        self.session = ""
        self.room_fingerprint = ""
        self.slot_name = ""
        self.placements: dict[int, dict[str, Any]] = {}
        self.sent_item_count = 0
        self.bridge_ready = False
        self.load_synchronized = False
        self.resync_requested = False
        self.goal_sent = False
        self.observed_checks: set[int] = set()
        self.death_count = 0
        self.last_ping = 0.0
        self.last_received_update = time.monotonic()
        self.pending_load: tuple[str, str, str, int] | None = None
        self.audit_requests: dict[str, dict[str, Any]] = {}
        self.pending_recovery: dict[str, Any] | None = None
        self.recovery_counter = 0
        self.committed_cursor = 0
        self.forced_save_hint = ""
        self.last_save_identity: SaveIdentity | None = None
        self.last_save_poll = 0.0
        self.last_save_stat: tuple[str, int, int] | None = None
        self.game_boot_id = ""
        self.game_load_epoch = 0
        self.last_scout_request = 0.0
        self.next_load_retry = 0.0

    async def server_auth(self, password_requested: bool = False) -> None:
        await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect(game=self.game)

    def pickup_safety_profile(self) -> str:
        options = self.slot_data.get("options", {})
        shuffled = [
            name
            for name, enabled in (
                ("key items", bool(int(options.get("shuffle_key_items", 0)))),
                ("quest items", bool(int(options.get("shuffle_quest_items", 0)))),
            )
            if enabled
        ]
        if not shuffled:
            return "conservative (vanilla key and quest pickups remain enabled)"
        return f"experimental pickup suppression ({' and '.join(shuffled)} randomized)"

    def on_package(self, cmd: str, args: dict[str, Any]) -> None:
        if cmd == "RoomUpdate" and self.slot_data:
            asyncio.create_task(self._evaluate_goal())
            return
        if cmd == "ReceivedItems":
            self.last_received_update = time.monotonic()
            if self.session:
                self.diagnostic.info(
                    "received_items_packet start=%s packet_count=%s authoritative_count=%s",
                    args.get("index"),
                    len(args.get("items", [])),
                    len(self.items_received),
                )
            return
        if cmd == "LocationInfo" and self.slot_data:
            self._maybe_configure_bridge()
            return
        if cmd != "Connected":
            return

        self.slot_data = args["slot_data"]
        seed = str(getattr(self, "seed_name", "unknown-seed"))
        self.slot_name = str(self.auth or self.player_names.get(self.slot or -1) or self.slot or "unknown-slot")
        canonical_slot_data = json.dumps(self.slot_data, sort_keys=True, separators=(",", ":"))
        identity = "\0".join(
            (
                seed,
                str(self.team),
                str(self.slot),
                self.slot_name,
                canonical_slot_data,
            )
        )
        full_digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        self.session = full_digest[:24]
        self.room_fingerprint = full_digest
        self.diagnostic.extra["session"] = self.session
        self.diagnostic.extra["room_fingerprint"] = self.room_fingerprint
        try:
            self.recovery_ledger = RecoveryLedger(
                self.bridge.root.parent,
                self.session,
                self.room_fingerprint,
                self.slot_name,
            )
        except RuntimeError as error:
            self.recovery_ledger = None
            self.bridge.reset(self.session, seed, self.slot_name)
            self.bridge_status = f"Cannot load recovery state: {error}"
            logger.error(self.bridge_status)
            self.diagnostic.exception(
                "recovery_ledger_open_failed session=%s room_fingerprint=%s",
                self.session,
                self.room_fingerprint,
            )
            return
        self.sent_item_count = 0
        self.committed_cursor = 0
        self.goal_sent = False
        self.observed_checks.clear()
        self.death_count = 0
        self.bridge_ready = False
        self.load_synchronized = False
        self.pending_load = None
        self.pending_recovery = None
        self.audit_requests.clear()
        self.placements.clear()
        self.locations_info.clear()
        self.locations_scouted.clear()
        self.bridge.reset(self.session, seed, self.slot_name)
        self.bridge_status = "Room identified; waiting for location metadata before enabling the game bridge."
        self.diagnostic.info(
            "room_connected session=%s room_fingerprint=%s seed=%s team=%s slot=%s slot_name=%r world_version=%s slot_data_sha256=%s locations=%s safety_profile=%r",
            self.session,
            self.room_fingerprint,
            seed,
            self.team,
            self.slot,
            self.slot_name,
            self.slot_data.get("world_version", "unknown"),
            hashlib.sha256(canonical_slot_data.encode("utf-8")).hexdigest(),
            len(self.server_locations),
            self.pickup_safety_profile(),
        )
        if "experimental" in self.pickup_safety_profile():
            logger.warning("Pickup safety profile: %s", self.pickup_safety_profile())
            self.diagnostic.warning("experimental_pickup_suppression_enabled")
        self.locations_scouted.update(self.server_locations)
        asyncio.create_task(
            self.send_msgs(
                [{"cmd": "LocationScouts", "locations": sorted(self.server_locations), "create_as_hint": 0}]
            )
        )
        self.last_scout_request = time.monotonic()
        self._maybe_configure_bridge()
        death_link = int(self.slot_data.get("options", {}).get("death_link", 0)) != 0
        asyncio.create_task(self.update_death_link(death_link))
        asyncio.create_task(self._evaluate_goal())

    def locations_in_logic(self):
        if not self.slot_data:
            return None
        options = self.slot_data.get("options", {})
        received_names = {
            ITEM_ID_TO_NAME[item.item]
            for item in self.items_received
            if item.item in ITEM_ID_TO_NAME
        }
        reached = reachable_regions(
            received_names,
            shuffle_key_items=bool(int(options.get("shuffle_key_items", 0))),
            shuffle_quest_items=bool(int(options.get("shuffle_quest_items", 0))),
        )
        enabled_ids = {
            int(row["location"]) for row in self.slot_data.get("markers", [])
        }
        completed = set(self.checked_locations) | self.observed_checks
        return [
            entry
            for entry in LOCATIONS
            if LOCATION_NAME_TO_ID[entry.name] in enabled_ids
            and LOCATION_NAME_TO_ID[entry.name] in self.server_locations
            and LOCATION_NAME_TO_ID[entry.name] not in completed
            and entry.region in reached
        ]

    def _build_placements(self) -> dict[int, dict[str, Any]]:
        marker_by_location = {
            int(row["location"]): row
            for row in self.slot_data.get("markers", [])
            if int(row.get("location", 0)) > 0
        }
        placements: dict[int, dict[str, Any]] = {}
        for location in self.server_locations:
            item = self.locations_info.get(location)
            if item is None:
                continue
            recipient = int(item.player)
            slot = self.slot_info.get(recipient)
            recipient_game = slot.game if slot else "Unknown Game"
            player = self.player_names.get(recipient, slot.name if slot else f"Player {recipient}")
            item_name = self.item_names.lookup_in_game(item.item, recipient_game)
            own = recipient == self.slot
            same_game = recipient_game == GAME
            title = item_name if own else f"{player}'s {item_name}"
            marker = marker_by_location.get(location, {})
            shop = marker.get("source") == "shop"
            if own:
                description = ""
            elif shop and same_game:
                description = (
                    f"An offering kept in Mournstead for {player}, another Lampbearer bound to this world."
                )
            elif shop:
                description = (
                    f"A strange offering kept by Mournstead's merchants for {player}; "
                    f"its true purpose lies in the world of {recipient_game}."
                )
            elif same_game:
                description = f"A relic belonging to {player}, another Lampbearer in Mournstead."
            else:
                description = (
                    f"A wayfaring relic bound for {player}; its true purpose lies in the world of {recipient_game}."
                )
            placements[location] = {
                "recipient": recipient,
                "player": player,
                "game": recipient_game,
                "item": int(item.item),
                "name": title,
                "own": own,
                "same_game": same_game,
                "description": description,
            }
        return placements

    def _maybe_configure_bridge(self, force: bool = False) -> None:
        if not self.slot_data or not self.session:
            return
        missing = self.server_locations - self.locations_info.keys()
        if missing and not force:
            self.bridge_status = f"Waiting for {len(missing)} location scout result(s) before enabling pickups."
            return
        self.placements = self._build_placements()
        self.bridge.configure(self.session, self.slot_data, self.checked_locations, self.placements)
        self.bridge_ready = True
        self.load_synchronized = False
        self.bridge_status = (
            f"Configured session {self.session}; waiting for the Lords of the Fallen UE4SS mod."
        )
        logger.info(self.bridge_status)
        self.diagnostic.info(
            "bridge_configured markers=%s items=%s placements=%s checked=%s force=%s",
            len(self.slot_data.get("markers", [])),
            len(self.slot_data.get("items", {})),
            len(self.placements),
            len(self.checked_locations),
            force,
        )

    def on_deathlink(self, data: dict[str, Any]) -> None:
        super().on_deathlink(data)
        if self.session:
            event_id = f"{data.get('time', time.time())}:{data.get('source', 'unknown')}"
            self.bridge.kill(self.session, event_id)

    async def game_loop(self) -> None:
        while not self.exit_event.is_set():
            try:
                if self.resync_requested and self.slot_data and self.session:
                    seed = str(getattr(self, "seed_name", "unknown-seed"))
                    self.sent_item_count = 0
                    self.load_synchronized = False
                    self.pending_load = None
                    self.pending_recovery = None
                    self.audit_requests.clear()
                    self.bridge.reset(self.session, seed, self.slot_name)
                    self.bridge_ready = False
                    self._maybe_configure_bridge()
                    self.resync_requested = False

                if (
                    self.slot_data
                    and not self.bridge_ready
                    and self.server_locations - self.locations_info.keys()
                    and time.monotonic() - self.last_scout_request >= 5
                ):
                    await self.send_msgs(
                        [{"cmd": "LocationScouts", "locations": sorted(self.server_locations), "create_as_hint": 0}]
                    )
                    self.last_scout_request = time.monotonic()
                    self.diagnostic.warning("location_scout_retry missing=%s", len(self.server_locations - self.locations_info.keys()))

                if self.bridge_ready:
                    await self._process_bridge_events()
                    if (
                        self.pending_load
                        and time.monotonic() - self.last_received_update >= 1.0
                        and time.monotonic() >= self.next_load_retry
                    ):
                        pending_load = self.pending_load
                        self.pending_load = None
                        self._start_load_recovery(*pending_load)
                    while self.load_synchronized and self.sent_item_count < len(self.items_received):
                        item = self.items_received[self.sent_item_count]
                        self.bridge.grant(self.session, self.sent_item_count, item.item)
                        self.diagnostic.info(
                            "grant_queued index=%s item_id=%s item=%r sender_slot=%s location=%s",
                            self.sent_item_count,
                            item.item,
                            ITEM_ID_TO_NAME.get(item.item, f"Unknown item {item.item}"),
                            item.player,
                            item.location,
                        )
                        self.sent_item_count += 1
                    if time.monotonic() - self.last_save_poll >= 2:
                        self._poll_save_changes()
                        self.last_save_poll = time.monotonic()
                    if time.monotonic() - self.last_ping >= 5:
                        self.bridge.ping(self.session)
                        self.last_ping = time.monotonic()
            except Exception:
                logger.exception("Lords of the Fallen client loop failed")
                self.diagnostic.exception("game_loop_failure")
            await asyncio.sleep(0.1)

    def _new_request_id(self, prefix: str) -> str:
        self.recovery_counter += 1
        return f"{prefix}-{self.client_run_id}-{self.recovery_counter}"

    def _identify_save(self, hint: str) -> tuple[SaveIdentity | None, str]:
        if self.forced_save_hint:
            path = self.save_tracker.root / self.forced_save_hint
            if path.is_file():
                return self.save_tracker.fingerprint(path), "used the explicit /save_slot selection"
            return None, f"explicitly selected save does not exist: {self.forced_save_hint}"
        known = self.recovery_ledger.known_digests if self.recovery_ledger else set()
        return self.save_tracker.identify(hint, known)

    def _start_load_recovery(self, boot_id: str, hint: str, durable_cursor: int, epoch: int) -> None:
        if not self.recovery_ledger or self.pending_recovery or self.audit_requests:
            return
        identity, reason = self._identify_save(hint)
        self.diagnostic.info(
            "load_identification boot=%s epoch=%s hint=%r result=%s reason=%r durable_cursor=%s",
            boot_id,
            epoch,
            hint,
            identity.digest if identity else "none",
            reason,
            durable_cursor,
        )
        if identity is None:
            self.bridge_status = (
                "Recovery is waiting for the first primary SaveNN.sav file."
                if reason.startswith("no primary")
                else "Recovery paused: the active SaveNN.sav file is ambiguous. Use /save_slot <0-99>."
            )
            logger.error(self.bridge_status)
            if reason.startswith("no primary"):
                self.pending_load = (boot_id, hint, durable_cursor, epoch)
                self.next_load_retry = time.monotonic() + 5
            return
        conflict = self.recovery_ledger.conflict(identity)
        if conflict:
            self.bridge_status = (
                "Recovery blocked: this save is bound to another Archipelago room/slot "
                f"({conflict.get('slot_name', 'unknown')}, {conflict.get('room_fingerprint', 'unknown')})."
            )
            logger.error(self.bridge_status)
            self.diagnostic.error(
                "save_seed_conflict save=%s digest=%s bound_session=%s bound_room=%s bound_slot=%r",
                identity.path,
                identity.digest,
                conflict.get("session"),
                conflict.get("room_fingerprint"),
                conflict.get("slot_name"),
            )
            return

        checkpoint = self.recovery_ledger.lookup(identity)
        if checkpoint is None and durable_cursor != 0:
            self.bridge_status = (
                "Recovery paused: this save has no checkpoint, but the bridge has prior grants for this room. "
                "Refusing to guess and duplicate items."
            )
            logger.error(self.bridge_status)
            self.diagnostic.error(
                "unknown_save_with_durable_grants digest=%s durable_cursor=%s action=refuse_blind_regrant",
                identity.digest,
                durable_cursor,
            )
            return

        recovery_id = self._new_request_id("recovery")
        cursor = int(checkpoint.get("cursor", 0)) if checkpoint else 0
        self.bridge.baseline(self.session, recovery_id, cursor)
        request_id = self._new_request_id("audit")
        self.audit_requests[request_id] = {
            "kind": "recover" if checkpoint else "initialize",
            "identity": identity,
            "checkpoint": checkpoint,
            "cursor": cursor,
            "recovery_id": recovery_id,
            "counts": {},
            "statuses": {},
        }
        self.last_save_identity = identity
        self.last_save_stat = (identity.path, identity.size, identity.mtime_ns)
        self.bridge.audit(self.session, request_id, "load_recovery")
        self.bridge_status = f"Auditing loaded save {Path(identity.path).name} before item delivery."
        self.diagnostic.info(
            "recovery_audit_requested request=%s recovery=%s digest=%s cursor=%s kind=%s received=%s",
            request_id,
            recovery_id,
            identity.digest,
            cursor,
            self.audit_requests[request_id]["kind"],
            len(self.items_received),
        )

    def _received_item_quantities(self, limit: int | None = None) -> list[tuple[int, int]]:
        rows = self.slot_data.get("items", {})
        result: list[tuple[int, int]] = []
        for item in self.items_received[:limit]:
            row = rows.get(str(item.item))
            if not row:
                self.diagnostic.error("unmapped_received_item item_id=%s location=%s sender=%s", item.item, item.location, item.player)
                result.append((int(item.item), 1))
            else:
                result.append((int(item.item), int(row.get("quantity", 1))))
        return result

    def _request_checkpoint_audit(self, identity: SaveIdentity, cursor: int, reason: str) -> None:
        if self.audit_requests or not self.load_synchronized:
            return
        request_id = self._new_request_id("checkpoint")
        self.audit_requests[request_id] = {
            "kind": "checkpoint",
            "identity": identity,
            "cursor": min(max(0, cursor), len(self.items_received)),
            "counts": {},
            "statuses": {},
        }
        self.bridge.audit(self.session, request_id, reason)
        self.diagnostic.info(
            "checkpoint_audit_requested request=%s digest=%s cursor=%s reason=%s",
            request_id,
            identity.digest,
            cursor,
            reason,
        )

    def _finish_audit(self, request_id: str, reported_count: int) -> None:
        request = self.audit_requests.pop(request_id, None)
        if request is None or not self.recovery_ledger:
            self.diagnostic.warning("unexpected_audit_end request=%s", request_id)
            return
        counts: dict[int, int | None] = request["counts"]
        unavailable = {item_id: status for item_id, status in request["statuses"].items() if counts.get(item_id) is None}
        self.diagnostic.info(
            "inventory_audit_complete request=%s kind=%s rows=%s reported=%s unavailable=%s",
            request_id,
            request["kind"],
            len(counts),
            reported_count,
            unavailable,
        )
        if unavailable or reported_count != len(self.slot_data.get("items", {})):
            self.bridge_status = "Recovery paused because one or more inventory quantities could not be measured safely."
            logger.error(self.bridge_status)
            return

        identity: SaveIdentity = request["identity"]
        definite_counts = {item_id: int(count) for item_id, count in counts.items() if count is not None}
        if request["kind"] == "checkpoint":
            self.recovery_ledger.checkpoint(identity, int(request["cursor"]), definite_counts)
            self.last_save_identity = identity
            self.last_save_stat = (identity.path, identity.size, identity.mtime_ns)
            self.diagnostic.info(
                "checkpoint_recorded digest=%s cursor=%s counts=%s",
                identity.digest,
                request["cursor"],
                definite_counts,
            )
            return

        checkpoint = request.get("checkpoint")
        if checkpoint is None:
            self.recovery_ledger.checkpoint(identity, 0, definite_counts)
            checkpoint = self.recovery_ledger.lookup(identity)
            self.diagnostic.info("initial_checkpoint_recorded digest=%s cursor=0", identity.digest)
        assert checkpoint is not None
        target_cursor = len(self.items_received)
        received = self._received_item_quantities(target_cursor)
        try:
            decisions = compute_recovery_decisions(checkpoint, received, counts)
        except ValueError as error:
            self.bridge_status = f"Recovery paused: {error}"
            logger.error(self.bridge_status)
            self.diagnostic.exception("recovery_decision_failure request=%s", request_id)
            return

        recovery_id = str(request["recovery_id"])
        expected: set[int] = set()
        for decision in decisions:
            item_name = ITEM_ID_TO_NAME.get(decision.item_id, f"Unknown item {decision.item_id}")
            self.diagnostic.info(
                "recovery_decision recovery=%s item_id=%s item=%r baseline=%s expected=%s current=%s restore=%s reason=%r",
                recovery_id,
                decision.item_id,
                item_name,
                decision.baseline,
                decision.expected,
                decision.current,
                decision.restore,
                decision.reason,
            )
            if decision.current is None:
                self.bridge_status = "Recovery paused because an item count is unavailable."
                logger.error(self.bridge_status)
                return
            if decision.restore:
                expected.add(decision.item_id)
                self.bridge.restore(
                    self.session,
                    recovery_id,
                    decision.item_id,
                    decision.restore,
                    decision.expected,
                    decision.current,
                )
        self.pending_recovery = {
            "id": recovery_id,
            "target_cursor": target_cursor,
            "expected": expected,
            "acknowledged": set(),
            "waiting_commit": False,
        }
        if not expected:
            self._commit_recovery()

    def _commit_recovery(self) -> None:
        if not self.pending_recovery or self.pending_recovery["waiting_commit"]:
            return
        self.pending_recovery["waiting_commit"] = True
        self.bridge.commit(
            self.session,
            self.pending_recovery["id"],
            self.pending_recovery["target_cursor"],
        )
        self.diagnostic.info(
            "recovery_commit_requested recovery=%s cursor=%s",
            self.pending_recovery["id"],
            self.pending_recovery["target_cursor"],
        )

    def _poll_save_changes(self) -> None:
        if not self.last_save_identity or self.audit_requests or not self.load_synchronized:
            return
        path = Path(self.last_save_identity.path)
        try:
            stat = path.stat()
        except OSError as error:
            self.diagnostic.warning("save_poll_failed path=%s error=%r", path, error)
            return
        current_stat = (str(path), stat.st_size, stat.st_mtime_ns)
        if current_stat == self.last_save_stat:
            return
        identity = self.save_tracker.fingerprint(path)
        self.last_save_stat = current_stat
        self._request_checkpoint_audit(identity, self.committed_cursor, "save_file_changed")

    def write_diagnostic_summary(self, reason: str) -> None:
        options = self.slot_data.get("options", {})
        self.diagnostic.info(
            "diagnostic_summary reason=%s session=%s room_fingerprint=%s seed=%s slot=%s slot_name=%r world_version=%s bridge_ready=%s load_synchronized=%s received=%s sent=%s committed_cursor=%s game_boot=%s load_epoch=%s safety_profile=%r shuffle_key_items=%s shuffle_quest_items=%s log=%s recovery_ledger=%s",
            reason,
            self.session or "none",
            self.room_fingerprint or "none",
            getattr(self, "seed_name", None),
            self.slot,
            self.slot_name,
            self.slot_data.get("world_version", "none"),
            self.bridge_ready,
            self.load_synchronized,
            len(self.items_received),
            self.sent_item_count,
            self.committed_cursor,
            self.game_boot_id or "none",
            self.game_load_epoch,
            self.pickup_safety_profile(),
            options.get("shuffle_key_items", 0),
            options.get("shuffle_quest_items", 0),
            self.diagnostic_log_path,
            self.recovery_ledger.path if self.recovery_ledger else "none",
        )

    async def _process_bridge_events(self) -> None:
        for event in self.bridge.read_events():
            if event.verb == "MALFORMED":
                reason = event.fields[-1] if event.fields else "unknown malformed record"
                logger.warning("Ignored malformed LotF bridge data: %s", reason)
                self.diagnostic.warning("malformed_bridge_record reason=%r", reason)
                continue
            if not event.fields or event.fields[0] != self.session:
                continue
            try:
                await self._handle_bridge_event(event)
            except (IndexError, TypeError, ValueError):
                logger.exception("Ignored invalid %s event from the LotF bridge", event.verb)
                self.diagnostic.exception("invalid_bridge_event verb=%s fields=%r", event.verb, event.fields)

    async def _handle_bridge_event(self, event: Any) -> None:
        if event.verb == "HELLO":
            version = event.fields[1] if len(event.fields) > 1 else "unknown"
            protocol = int(event.fields[2]) if len(event.fields) > 2 else 0
            boot_id = event.fields[3] if len(event.fields) > 3 else "unknown"
            if protocol != 3:
                self.bridge_status = f"Bridge protocol mismatch: client 3, mod {protocol}. Reinstall the matching package."
                logger.error(self.bridge_status)
                self.diagnostic.error("protocol_mismatch client=3 mod=%s version=%s", protocol, version)
                self.bridge_ready = False
                return
            expected_version = str(self.slot_data.get("world_version", "unknown"))
            if version != expected_version:
                self.bridge_status = (
                    f"Package mismatch: room/APWorld {expected_version}, game mod {version}. "
                    "Reinstall both files from the same release."
                )
                logger.error(self.bridge_status)
                self.diagnostic.error(
                    "package_version_mismatch world_version=%s mod_version=%s protocol=%s",
                    expected_version,
                    version,
                    protocol,
                )
                self.bridge_ready = False
                return
            self.game_boot_id = boot_id
            self.bridge_status = (
                f"Game bridge connected (mod {version}, session {self.session}, boot {boot_id}); "
                f"{self.pickup_safety_profile()}."
            )
            logger.info(self.bridge_status)
            self.diagnostic.info("bridge_hello mod_version=%s protocol=%s boot=%s", version, protocol, boot_id)
        elif event.verb == "LOADED" and len(event.fields) >= 6:
            boot_id = event.fields[1]
            epoch = int(event.fields[2])
            reason = event.fields[3]
            hint = event.fields[4]
            durable_cursor = int(event.fields[5])
            self.game_boot_id = boot_id
            self.game_load_epoch = epoch
            self.load_synchronized = False
            self.pending_recovery = None
            self.audit_requests.clear()
            self.pending_load = (boot_id, f"{reason}|{hint}", durable_cursor, epoch)
            self.diagnostic.info(
                "game_save_loaded boot=%s epoch=%s reason=%r hint=%r durable_cursor=%s",
                boot_id,
                epoch,
                reason,
                hint,
                durable_cursor,
            )
        elif event.verb == "SAVED" and len(event.fields) >= 5:
            boot_id = event.fields[1]
            epoch = int(event.fields[2])
            cursor = int(event.fields[3])
            hint = event.fields[4]
            identity, reason = self._identify_save(hint)
            self.diagnostic.info(
                "game_save_event boot=%s epoch=%s cursor=%s hint=%r digest=%s identification=%r",
                boot_id,
                epoch,
                cursor,
                hint,
                identity.digest if identity else "none",
                reason,
            )
            if identity and self.recovery_ledger and not self.recovery_ledger.conflict(identity):
                self._request_checkpoint_audit(identity, cursor, "save_manager_event")
        elif event.verb == "COUNT" and len(event.fields) >= 5:
            request_id = event.fields[1]
            request = self.audit_requests.get(request_id)
            if request is not None:
                item_id = int(event.fields[2])
                raw_count = int(event.fields[3])
                request["counts"][item_id] = None if raw_count < 0 else raw_count
                request["statuses"][item_id] = event.fields[4]
        elif event.verb == "COUNT_END" and len(event.fields) >= 6:
            request_id = event.fields[1]
            self.game_boot_id = event.fields[2]
            self.game_load_epoch = int(event.fields[3])
            self.committed_cursor = int(event.fields[4])
            self._finish_audit(request_id, int(event.fields[5]))
        elif event.verb == "CHECK" and len(event.fields) >= 2:
            location = int(event.fields[1])
            if location in self.server_locations and location not in self.checked_locations:
                self.observed_checks.add(location)
                await self.check_locations({location})
                await self._evaluate_goal()
                self.diagnostic.info(
                    "location_check_sent location_id=%s location=%r replay_or_live=true",
                    location,
                    next((entry.name for entry in LOCATIONS if LOCATION_NAME_TO_ID[entry.name] == location), "unknown"),
                )
        elif (
            event.verb == "GOAL"
            and not self.goal_sent
            and int(self.slot_data.get("options", {}).get("goal", 0)) == Goal.option_any_ending
        ):
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            self.goal_sent = True
            logger.info("Goal completed in Lords of the Fallen.")
            self.diagnostic.info("goal_complete mode=any_ending")
        elif event.verb == "DEATH":
            await self._handle_local_death(event)
            self.diagnostic.info("local_death_event mode=%s", self.slot_data.get("options", {}).get("death_link", 0))
        elif event.verb == "LOG" and len(event.fields) >= 2:
            logger.info("[LotF] %s", event.fields[1])
            self.diagnostic.info("game_log message=%r", event.fields[1])
        elif event.verb == "ERROR" and len(event.fields) >= 2:
            logger.error("[LotF] %s", event.fields[1])
            self.diagnostic.error("game_error message=%r", event.fields[1])
        elif event.verb == "ACK" and len(event.fields) >= 3:
            self._handle_bridge_ack(event.fields)

    def _handle_bridge_ack(self, fields: tuple[str, ...]) -> None:
        command = fields[1]
        command_id = fields[2]
        if command == "GRANT":
            index = int(command_id)
            self.committed_cursor = max(self.committed_cursor, index + 1)
            self.diagnostic.info(
                "grant_ack index=%s item_id=%s quantity=%s detail=%r committed_cursor=%s",
                index,
                fields[3] if len(fields) > 3 else "unknown",
                fields[4] if len(fields) > 4 else "unknown",
                fields[5:] if len(fields) > 5 else (),
                self.committed_cursor,
            )
        elif command == "RESTORE" and self.pending_recovery:
            recovery_id = command_id
            item_id = int(fields[3])
            quantity = int(fields[4])
            before = fields[5] if len(fields) > 5 else "unknown"
            after = fields[6] if len(fields) > 6 else "unknown"
            if recovery_id == self.pending_recovery["id"]:
                self.pending_recovery["acknowledged"].add(item_id)
                self.diagnostic.info(
                    "recovery_restore_ack recovery=%s item_id=%s item=%r quantity=%s before=%s after=%s",
                    recovery_id,
                    item_id,
                    ITEM_ID_TO_NAME.get(item_id, f"Unknown item {item_id}"),
                    quantity,
                    before,
                    after,
                )
                if self.pending_recovery["acknowledged"] >= self.pending_recovery["expected"]:
                    self._commit_recovery()
        elif command == "COMMIT" and self.pending_recovery and command_id == self.pending_recovery["id"]:
            cursor = int(fields[3])
            self.committed_cursor = cursor
            self.sent_item_count = cursor
            self.load_synchronized = True
            restored = len(self.pending_recovery["acknowledged"])
            self.pending_recovery = None
            self.bridge_status = f"Save synchronized at received-item cursor {cursor}; normal delivery enabled."
            logger.info(self.bridge_status)
            self.diagnostic.info("recovery_committed cursor=%s restored_item_types=%s", cursor, restored)
        else:
            self.diagnostic.debug("bridge_ack command=%s id=%s fields=%r", command, command_id, fields[3:])

    async def _evaluate_goal(self) -> None:
        if self.goal_sent or not self.slot_data:
            return
        options = self.slot_data.get("options", {})
        if int(options.get("goal", 0)) != Goal.option_all_bosses:
            return
        required = {int(location) for location in self.slot_data.get("goal_locations", [])}
        completed = set(self.checked_locations) | self.observed_checks
        if required and required.issubset(completed):
            await self.send_msgs(
                [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
            )
            self.goal_sent = True
            logger.info("All Bosses goal completed: every route-stable boss stigma is checked.")

    async def _handle_local_death(self, event: Any) -> None:
        options = self.slot_data.get("options", {})
        mode = int(options.get("death_link", 0))
        if mode == 0:
            return
        self.death_count += 1
        amnesty = int(options.get("death_link_amnesty", 1))
        if self.death_count < amnesty:
            logger.info("DeathLink amnesty: %d/%d deaths.", self.death_count, amnesty)
            return
        self.death_count = 0
        await self.send_death(f"{self.auth or 'The Lampbearer'} fell in Mournstead.")


async def main(args: Namespace) -> None:
    context = LordsOfTheFallenContext(args.connect, args.password)
    game_task: asyncio.Task | None = None
    try:
        context.auth = args.name
        context.server_task = asyncio.create_task(server_loop(context), name="server loop")
        if gui_enabled and not getattr(args, "nogui", False):
            context.run_gui()
        context.run_cli()
        game_task = asyncio.create_task(context.game_loop(), name="LotF game bridge")
        await context.exit_event.wait()
    finally:
        if game_task:
            game_task.cancel()
        context.write_diagnostic_summary("shutdown")
        await context.shutdown()
        close_diagnostic_logger(context.diagnostic)
