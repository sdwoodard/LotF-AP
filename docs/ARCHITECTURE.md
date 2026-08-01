# Architecture

```text
Archipelago server
        |
        | WebSocket protocol
        v
AP CommonClient (inside lotf.apworld)
        |
        | versioned, append-only line protocol
        v
%LOCALAPPDATA%\LotFArchipelago\bridge
        |
        v
UE4SS LotFArchipelago Lua mod
        |
        | reflected UFunction/UItemData calls
        v
Lords of the Fallen (offline, no EAC)
```

The APWorld owns generation, item/location IDs, region rules, and slot data.
The CommonClient owns the network connection and translates AP packets into
idempotent game commands. Lua is intentionally network-free: it observes the
game, grants mapped assets, and writes small events to disk.

## Identity, logging, and replay safety

A session key is the first 24 hexadecimal characters of SHA-256 over the room
seed, team, slot, slot name, and canonical slot data. The full digest is the
room fingerprint written to `%LOCALAPPDATA%\LotFArchipelago\logs\lotf-client.log`.
On Linux, the native client uses
`${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago`; the Proton launcher
maps the game process to that same physical directory. `LOTF_AP_DATA_DIR`,
`LOTF_AP_GAME_DATA_DIR`, and `LOTF_AP_SAVE_DIR` provide explicit overrides.
The seed name in that same record identifies the matching generated
`.archipelago`/multiworld output. The private logger appends across launches and
rotates at 10 MiB while retaining five prior files. It intentionally does not
record the server password or general room chat.

Lua persists completed `CHECK`, `GRANT`, and `KILL` records under the session.
After every `READY`, it replays any locally durable check the server has not
reported as checked. This closes the client-exit window between observing a
pickup and delivering its `LocationChecks` packet.

Received-item recovery uses a stronger save checkpoint:

1. The client fingerprints the active primary `SaveNN.sav` with SHA-256.
2. At each game save, protocol v3 records the receive cursor and measured count
   of every mapped item beside that fingerprint using an atomic JSON update.
3. On load, the client adds only receipts after that checkpoint cursor to its
   recorded baseline and compares the result with the inventory now loaded.
4. Lua grants only a measured deficit, measures again after the grant, and then
   commits the new cursor. If either measurement is unavailable, recovery stops
   instead of risking a duplicate.

This restores stackable as well as unique items after a crash or deliberate
rollback without recreating consumables legitimately spent before the loaded
checkpoint. Save fingerprints and primary `SaveNN.sav` paths are also bound to
a room and slot; loading a save previously used by another seed is blocked. If multiple character saves
make automatic identification ambiguous, `/save_slot <0-99>` selects the
active `SaveNN.sav` explicitly. The AP server remains authoritative for checked
locations and received-item history.

## Why asset markers

The Steam build's IoStore directory index exposes cooked `/Game/...` paths and
the executable exposes reflected UFunction names. Unique `UItemData` classes
survive ASLR and ordinary code-layout changes, unlike pointer chains or raw
offsets. The bridge observes these classes when inventory-add functions run.
Progression suppression replaces the incoming class parameter with a harmless
filler item before the vanilla add executes.

## Protocol

Each record is an ASCII verb followed by percent-encoded, tab-separated fields.
Commands include configuration, placement-presentation, inventory-audit,
recovery, DeathLink, and health records. Events include lifecycle, inventory
counts, checks, goals, acknowledgements, and diagnostics. See
[PROTOCOL.md](PROTOCOL.md) for field layouts.
