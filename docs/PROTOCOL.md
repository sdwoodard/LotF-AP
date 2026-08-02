# Game bridge protocol v7

All fields are percent-encoded UTF-8-compatible ASCII. Records end in LF.
Every command after `RESET` and every event begins with the current session.

## Client to game

| Verb | Fields after verb |
| --- | --- |
| `RESET` | protocol, session, seed, slot |
| `MARK` | session, location ID, marker, suppress (0/1), shop (0/1), normalized pickup FGuid, retail row label |
| `ITEM` | session, item ID, Unreal class path, quantity, item name, unique (0/1) |
| `PLACE` | session, location ID, recipient slot, player, game, item ID, display name, own (0/1), same game (0/1), description |
| `CHECKED` | session, location ID |
| `OPTIONS` | session, DeathLink mode, delivery delay ms, goal mode |
| `READY` | session |
| `GRANT` | session, received-item index, item ID |
| `BASELINE` | session, recovery ID, checkpoint receive cursor |
| `AUDIT` | session, request ID, reason |
| `RESTORE` | session, recovery ID, item ID, deficit quantity, expected count, observed count |
| `COMMIT` | session, recovery ID, new receive cursor |
| `KILL` | session, globally unique event ID |
| `PING` | session |

## Game to client

| Verb | Fields after verb |
| --- | --- |
| `HELLO` | session, mod version, protocol version, game-process boot ID |
| `LOADED` | session, boot ID, load epoch, reason, save-slot hint, durable grant cursor |
| `SAVED` | session, boot ID, load epoch, receive cursor, save-slot hint |
| `COUNT` | session, request ID, item ID, count (`-1` if unavailable), status |
| `COUNT_END` | session, request ID, boot ID, load epoch, receive cursor, row count |
| `CHECK` | session, location ID |
| `GOAL` | session (Any Ending credits callback only) |
| `DEATH` | session, reserved flag |
| `ACK` | session, command type, command ID |
| `LOG` | session, text |
| `ERROR` | session, text |

Readers tolerate truncation and stale records, reject records over 64 KiB, and
cap the number processed in one Lua tick. Python replaces the command file
atomically on `RESET` and starts at the end of an existing event file rather
than truncating while the game may be writing. A new `RESET` clears in-memory
configuration; durable state remains namespaced by session.

`RESTORE` is not a blind replay. Lua measures the current stock immediately
before granting, clamps the quantity to `expected - current`, measures again,
and acknowledges the observed before/after counts. `COMMIT` is sent only after
every required item type is acknowledged. A missing count leaves delivery
paused and produces a diagnostic error.

Normal `GRANT` delivery uses the same before/after verification. A mapped
unique item already present is acknowledged without adding another copy;
stackable items use a fixed expected target. If a reflected call succeeds but
the target is not yet observed, automatic mutation retries pause while the
bridge continues to re-measure. This fail-closed rule prevents a delayed game
update from turning a fallback or retry into a duplicate; `/resync` starts a
fresh measured reconciliation after the player checks the inventory.

The Python client evaluates `all_bosses` from the required checked-location ID
set. The Lua bridge emits `GOAL` only for `any_ending`, after the reflected
`HexFinishGameManager.OnCreditScreenEndedCallback` runs. This avoids treating
an ending-specific inventory object as completed credits.
