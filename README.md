<p align="center">
  <img src=".github/assets/lotf-icon.png" width="176" alt="The transparent Lords of the Fallen iron-cross icon">
</p>

<h1 align="center">Lords of the Fallen Archipelago</h1>

<p align="center">
  An Archipelago multiworld randomizer client and offline UE4SS mod for
  <em>Lords of the Fallen</em> (2023) on PC.
</p>

<p align="center">
  <img alt="Version 0.2.0" src="https://img.shields.io/badge/version-0.2.0-b76e45">
  <img alt="Archipelago 0.6.7 or newer" src="https://img.shields.io/badge/Archipelago-0.6.7%2B-6d5dfc">
  <img alt="Windows and Linux through Proton" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%2FProton-4a90a4">
  <img alt="MIT license" src="https://img.shields.io/badge/license-MIT-3c9b5f">
</p>

> [!WARNING]
> Version 0.2.0 is a development release for Steam build 24429019. Back up
> your saves, use a new character for every seed, disable Easy Anti-Cheat, and
> keep the game offline. Never use the mod in matchmaking, co-op, or invasions.

> [!IMPORTANT]
> Generate a new multiworld after installing 0.2.0. Rooms generated with a
> 0.1.x APWorld contain the old 58-location table and cannot gain the new
> physical checks retroactively.

The project couples a normal `.apworld` to a UE4SS Lua bridge. Archipelago
runs outside the game; the bridge observes randomized checks, presents remote
items in-game, and grants received Lords of the Fallen items. Compatibility is
validated against the game executable and reflected IoStore names instead of
hard-coded memory addresses.

## Contents

- [What is included](#what-is-included)
- [Requirements](#requirements)
- [Download and install](#download-and-install)
  - [Windows](#windows)
  - [Linux and Proton](#linux-and-proton)
- [Startup order and reconnection](#startup-order-and-reconnection)
- [Client commands](#client-commands)
- [Logic and safety](#logic-and-safety)
- [Crash recovery and diagnostics](#crash-recovery-and-diagnostics)
- [Build and test](#build-and-test)
- [Scope, support, and license](#scope-support-and-license)

## What is included

| Component | Purpose |
| --- | --- |
| `lotf.apworld` | Generates Lords of the Fallen slots and adds the game client to Archipelago Launcher. |
| UE4SS game mod | Detects checks, grants received items, displays remote items, and persists bridge state. |
| Player options | Provides a thoroughly commented starting YAML with the intended 0.2.0 defaults. |
| Install packages | Includes separate Windows/PowerShell and Linux/Bash installers, launchers, uninstallers, and diagnostic tools. |
| Developer tools | Validates source/assets, audits the installed game, tests generation matrices, and builds reproducible release archives. |

Important features include:

- 597 retail pre-placed world pickups, with only the tutorial Throwing Stone
  deliberately kept vanilla;
- `any_ending` and a route-safe `all_bosses` goal;
- protected missable checks and excluded grind-heavy faction/Crucible sources;
- optional Vigor Skull and weapon-upgrade smoothing with `off`, `semi`, and
  `full` strengths;
- `/logic` for region-prefixed, currently reachable unchecked locations;
- durable check replay and inventory-measured rollback recovery;
- rotating, room-linked logs and privacy-conscious support bundles;
- native local-item presentation, named same-game remote items, and a
  transparent Archipelago icon for other-game items; and
- support for stable UE4SS 3.0.x (`Win64\Mods`) and newer
  (`Win64\ue4ss\Mods`) directory layouts.

## Requirements

- The Steam release of *Lords of the Fallen* on Windows 10/11, or on Linux
  through Steam Proton.
- [Archipelago 0.6.7 or newer](https://github.com/ArchipelagoMW/Archipelago/releases).
- [RE-UE4SS 3.0.1](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/v3.0.1),
  using its basic `UE4SS_v3.0.1.zip` package.
- Easy Anti-Cheat disabled and the game kept offline for the entire modded
  session.

RE-UE4SS is the Unreal Engine mod loader that runs the included Lua bridge
inside the game. It is a separate open-source project and is not included in
this release. Download the basic package from the
[official RE-UE4SS 3.0.1 release](https://github.com/UE4SS-RE/RE-UE4SS/releases/download/v3.0.1/UE4SS_v3.0.1.zip),
not a source-code, `zDEV`, or experimental archive.

The installers modify only the `LotFArchipelago` mod directory and its
`mods.txt` entry. The complete platform packages also retain the mod payload
under `game-mod/LotFArchipelago` for inspection or manual installation.

## Download and install

Download the release package for your platform from GitHub Releases. It
contains the APWorld, game mod, example player YAML, documentation, and the
appropriate platform scripts.

### Windows

1. Back up `%LOCALAPPDATA%\LOTF2\Saved\SaveGames` and use a new character for
   each seed.
2. In Steam, right-click **Lords of the Fallen** and choose
   **Manage > Browse local files**. The folder Steam opens is the game folder;
   it contains `LOTF2.exe` and a `LOTF2` subfolder. The exact drive and Steam
   library are different for each user.
3. Download the basic `UE4SS_v3.0.1.zip` from the official link above. Open
   the game folder, then open `LOTF2\Binaries\Win64`. Extract the *contents* of
   the UE4SS ZIP directly into `Win64` so the layout includes entries such as:

   ```text
   Lords of the Fallen/
   `-- LOTF2/Binaries/Win64/
       |-- dwmapi.dll
       |-- UE4SS.dll
       `-- Mods/
   ```

   Do not leave everything inside an extra `UE4SS_v3.0.1` folder. UE4SS will
   create `UE4SS.log` in `Win64` when it loads.
4. Download both `LotF-Archipelago-x.y.z-win64.zip` and
   `LotF-Archipelago-Windows-Installer-x.y.z.zip`. Use **Extract All** on the
   small Windows Installer ZIP, open that folder, and double-click
   **`Install-LotFArchipelago.cmd`**. Do not extract the `-win64.zip` yourself;
   select that ZIP when the file picker asks for it, then select the game folder
   from step 2. The installer uses a temporary extraction, installs the mod,
   copies the APWorld, YAML, documentation, and player tools beside itself, and
   removes the temporary files afterward.

   The `.cmd` wrapper uses a process-local execution-policy bypass, so Windows'
   normal “script execution is disabled” setting does not block it. As a manual
   alternative, extract the full `-win64.zip` and run its copy of the same
   installer.
5. In Archipelago Launcher, select **Install APWorld** and choose the
   `lotf.apworld` now beside the guided installer. Double-clicking the file is
   also supported on Windows.
6. Edit `Lords of the Fallen.yaml`, place it in Archipelago's `Players`
   directory, and generate locally. A locally generated multiworld can be
   uploaded to the normal Archipelago host afterward.
7. Put Steam in **Offline Mode**, but leave Steam running and signed into the
   account that owns the full game. Open **Lords of the Fallen Client** and
   connect to the room and slot. Then double-click **`Start-LotF-AP.cmd`**,
   select the game folder when asked, and accept the offline-use warning.
8. Do not load the character until the client reports `Game bridge connected`
   and save synchronization completes.

Always use `Start-LotF-AP.cmd` for a modded session. It disables the anti-cheat
launch path and supplies the full game's Steam AppID (`1501750`) to the child
process. This prevents the shipping executable from being mistaken for the
limited Free Friend's Pass (`3664720`). If the game still displays Friend's
Pass, close it, confirm the signed-in Steam account owns the full game, verify
the game files in Steam, start the unmodded full game once while online, then
return Steam to Offline Mode and retry the guided launcher. Do not create a
`steam_appid.txt` file; the launcher refuses that unsupported workaround.

To remove the mod, double-click `Uninstall-LotFArchipelago.cmd` and select the
game folder. It removes only this project's mod and `mods.txt` entry; it leaves
UE4SS, saves, logs, backups, and other mods unchanged.

### Linux and Proton

Archipelago's Linux AppImage cannot currently install custom APWorlds. Use an
Archipelago 0.6.7+ source checkout, extract
`LotF-Archipelago-x.y.z-linux.zip`, and run:

```bash
bash ./install-apworld.sh --archipelago-path "$HOME/src/Archipelago"
bash ./install-lotf-archipelago.sh \
  --game-path "$HOME/.local/share/Steam/steamapps/common/Lords of the Fallen"
```

Start the source checkout with `python3 Launcher.py`, open **Lords of the
Fallen Client**, and connect. Then launch the offline Proton process:

```bash
bash ./start-lotf-ap.sh \
  --game-path "$HOME/.local/share/Steam/steamapps/common/Lords of the Fallen"
```

The launcher usually finds Proton automatically. If it does not, pass
`--proton /path/to/proton` and
`--compat-data /path/to/compatdata/1501750`. The native client and Proton
bridge share `${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago`; override
that with `LOTF_AP_DATA_DIR`. Use `LOTF_AP_SAVE_DIR` for a nonstandard save
prefix.

Linux/Proton support is developmental. Back up the Proton save directory and
repeat an offline main-menu smoke test after every game, Proton, or UE4SS
update.

## Startup order and reconnection

The recommended order is:

1. Open **Lords of the Fallen Client**.
2. Connect it to the correct room and slot.
3. Start Lords of the Fallen offline.
4. Wait for `Game bridge connected`.
5. Load the seed's character and wait for the save synchronization message
   before moving or collecting anything.

Starting the client before the game is safe; it waits for the file bridge.
Starting the game first is also safe only while you remain at the title screen
or main menu. Do not load a character or collect checks until the client has
connected to the bridge, because unconfigured pickup hooks cannot report or
safely suppress randomized checks.

If the client closes while the game remains open, pause play and reopen it.
The mod persists observed checks locally and replays any the server has not
acknowledged after reconnection. The client then audits received items against
the active save before restoring a measured deficit. Reconnect to the same
room, slot, and seed character, wait for both bridge and save synchronization,
and run `/resync` if requested. A room/character mismatch intentionally blocks
automatic recovery rather than risking cross-seed item delivery.

## Client commands

| Command | Result |
| --- | --- |
| `/bridge` | Shows mod/package versions, connection state, and the active pickup-safety profile. |
| `/logic [page or area]` or `/inlogic` | Lists unchecked locations currently reachable with received items, 30 per page. Use an area prefix such as `/logic AR` to filter; every row includes that prefix and a short location description. |
| `/resync` | Starts a fresh measured inventory reconciliation after a crash, rollback, or paused grant. |
| `/save_slot <0-99>` | Selects a save slot when automatic save detection is ambiguous. |
| `/diagnostics` | Writes a room-linked diagnostic summary to the log. |

Boss checks are sent by soulflaying their remembrance stigmas. The `/logic`
description identifies the check's location; it does not describe the
randomized item placed there.

## Logic and safety

All 597 eligible pre-placed world pickups are checks and have their vanilla
inventory item suppressed. The beginning Throwing Stone remains vanilla so the
player can always knock down hanging corpses. The default player template
enables traversal-key and quest-object shuffling, permits keys to cross worlds,
and leaves both early-key guarantees off. The optional **Safe First Seed** web
preset retains vanilla key and quest objects for build validation. The active
suppression profile is reported by `/bridge` and diagnostics.

Every physical pickup GUID has been resolved to its cooked gameplay sublevel
and assigned to an explicit base or keyed logic region. The checked-in audit
covers all 597 identities and is protected by a stable digest; generation and
the client's `/logic` command use the same region graph. The default upgrade
counts reproduce one normal +10 weapon set, all 20 Sanguinarix upgrade
materials, and all three lamp upgrades. Optional smoothing can keep low-value
Vigor Skulls and Small Deralium toward early logical checks, with the larger
tiers later; `semi` retains more local variation and `full` applies the
strongest low-to-high ordering.

Every item classified as advancement unlocks at least one check. This includes
the four quest objects that unlock the Umbral-Tinged Flayed Skin, Elegant
Perfume, and Restored Sentinel Banner checks. Progression and broadly useful
items cannot be placed at those or other protected missable quest checks.
Faction rewards and Crucible/boss-rush encounters are excluded from the
location pool. `all_bosses` contains only audited encounters that remain
available regardless of ending route and quest choices; ending-specific or
quest-lockable bosses do not count.

See [Progression and location safety](docs/PROGRESSION.md) for the complete
advancement list, unsafe-location rules, excluded sources, and boss set. These
guarantees are enforced by the repository's automated tests.

## Crash recovery and diagnostics

After a game crash or an older-save load, leave the client connected and let
the game finish loading. The client fingerprints the active `SaveNN.sav`,
audits actual inventory counts, and restores only the deficit from items the
server says this slot received. Unique items already present are not granted
again; stackable items are restored only up to their expected count. An
unverifiable mutation fails closed and asks for manual inspection instead of
blindly retrying.

Logs append across sessions and include the room fingerprint, slot,
APWorld/mod version, safety profile, delivery decisions, game boot/load IDs,
and recovery counts:

- Windows: `%LOCALAPPDATA%\LotFArchipelago\logs\lotf-client.log`
- Linux: `${XDG_STATE_HOME:-$HOME/.local/state}/LotFArchipelago/logs/lotf-client.log`

Create a basic support archive by double-clicking
`New-LotFDiagnosticBundle.cmd` on Windows, or run
`New-LotFDiagnosticBundle.ps1` with attachment paths for an advanced report.
On Linux use `new-lotf-diagnostic-bundle.sh`. Supplying the game path includes the
executable identity and UE4SS log. Supplying the generated multiworld and
player YAML ties the report to its seed. The bundle intentionally excludes
game saves and server passwords; review it before sharing.

## Build and test

The repository separates platform-specific tooling while keeping shared
Python utilities in `scripts/common`:

```text
scripts/
|-- common/      # Cross-platform Python validation/generation tools
|-- linux/       # Bash build, validation, generation, and asset scripts
`-- windows/     # PowerShell build, validation, generation, and asset scripts

installer/
|-- linux/       # Bash installer, launcher, uninstaller, and diagnostics
`-- windows/     # PowerShell installer, launcher, uninstaller, and diagnostics
```

The release version is read from `VERSION`. Both build paths produce:

- `lotf.apworld`
- `LotF-Archipelago-x.y.z-win64.zip`
- `LotF-Archipelago-x.y.z-linux.zip`
- `LotF-Archipelago-Windows-Installer-x.y.z.zip`

Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\Test-Repository.ps1 `
  -GamePath "<Steam game folder>"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\Build-Release.ps1 `
  -GamePath "<Steam game folder>"
```

Pass `-RetocPath <retoc.exe>` for exact cooked-path and reflected-object
checks. Development also auto-detects a sibling `.tools\retoc\retoc.exe`; it
is never packaged.

Linux (requires `python3` and `zip`):

```bash
bash ./scripts/linux/test-repository.sh \
  --game-path "$HOME/.local/share/Steam/steamapps/common/Lords of the Fallen"
bash ./scripts/linux/build-release.sh \
  --game-path "$HOME/.local/share/Steam/steamapps/common/Lords of the Fallen"
```

For the exhaustive single-game, same-game multiworld, and mixed-game matrix,
build `lotf.apworld` and run either:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\Test-GenerationMatrix.ps1 `
  -ArchipelagoPath "<Archipelago source checkout>"
```

```bash
bash ./scripts/linux/test-generation-matrix.sh \
  --archipelago-path "$HOME/src/Archipelago"
```

See [Development](docs/DEVELOPMENT.md) for unit-test commands and acceptance
criteria. Runtime hooks still require a clean offline game-process smoke test
after every game or UE4SS update.

## Scope, support, and license

This version randomizes every eligible pre-placed physical pickup represented
in the retail game's stable random-loot map, including duplicated consumable
and equipment pickup actors, plus mapped boss/key/quest/stigma checks. The
tutorial Throwing Stone remains vanilla. Enemy drops, destructible drops,
shop purchases, faction rewards, Crucible rewards, enemy placement, entrances,
and online play are outside the current scope.

For support, contact `sigmar.heldenhammer` on Discord (user ID
`307218166944104448`). Include a short problem description, approximate time,
diagnostic bundle, and, when safe, the matching generated multiworld and player
YAML.

This unofficial fan project is unaffiliated with HEXWORKS, CI Games, Epic
Games, Valve/Steam, or Archipelago. Source code is available under the
[MIT License](LICENSE); game artwork and trademarks remain the property of
their respective owners.
