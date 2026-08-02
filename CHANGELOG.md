# Changelog

## 0.2.2 - 2026-08-02

- Discover Blueprint-derived world pickups through the game's reflected
  pickup registry and watch newly streamed pickup actors. The previous exact
  native-class scan found no retail pickup actors, so 0.2.1 left vanilla loot
  in place and reported no checks.
- Prepare curated key and quest pickups such as Flayed Skin through their item
  marker when the actor is not represented by the pre-placed random-loot map.
- Add resilient generated-class lookup after loading an item package so pickup
  suppression, received-item delivery, recovery audits, and same-game icons
  can resolve retail item assets across supported UE4SS lookup behaviors.
- Remove the redundant release-package picker from the Windows installer. The
  installer now uses the mod and APWorld files beside itself in the extracted
  release and asks only for the Steam game folder.
- Advance the client/game bridge protocol to v7 so mixed 0.2.1/final 0.2.2
  files—and the intermediate runtime-test build—fail closed instead of
  silently running incompatible code.

## 0.2.1 - 2026-08-02

- Prepare loaded physical pickups by their persistent retail GUID before the
  player interacts with them, and correlate the prepared inventory object with
  its generated location. This fixes 0.2.0 runs that retained vanilla pickups
  and never reported checks.
- Observe interaction-component, pickup-completion, and inventory-added events,
  with detailed preparation/check logging and the tutorial Throwing Stone
  still explicitly preserved.
- Fail closed on a client/mod protocol mismatch and avoid registering gameplay
  hooks until a compatible client has completed bridge configuration.
- Remove speculative reflected method calls on arbitrary hook values that could
  crash UE4SS while a title-screen character object was being initialized.
- Start the game with offline/Redpoint EOS suppression flags and append launch
  decisions to the diagnostic log while retaining the full-game Steam AppID.
  The bridge also disables the game's online-mode, crossplay, and invasion
  settings directly.
- Replace the Windows installation prompts with a single installer window,
  progress display, and read-only output log. The selected game path is saved
  for one-click start, uninstall, and diagnostic scripts.
- Consolidate Windows distribution into
  `LotF-Archipelago-0.2.1-win64.zip`; the separate bootstrap installer archive
  is no longer produced.
- Streamline player documentation and provide a correctly sized, separate
  GitHub social-preview asset.

## 0.2.0 - 2026-08-01

- Expanded the physical location pool from curated unique pickups to all 597
  eligible entries in the retail pre-placed-loot map. The tutorial Throwing
  Stone remains vanilla.
- Resolved every pickup GUID to its cooked gameplay sublevel and added explicit
  keyed subregions, chained goal requirements, a stable logic-audit digest,
  and per-edge/sphere generation checks.
- Made key and quest shuffle the default, with remote keys allowed and early
  Pilgrim's Perch/Fief guarantees disabled by default. `accessibility: full`
  is the template and APWorld default.
- Reclassified Flayed Skin, Spurned Progeny Eyeball, Ancient Sentinel Banner,
  and Tattered Sentinel Banner as advancement because they unlock protected
  quest checks; generation and `/logic` now enforce those item dependencies.
- Added optional `off`, `semi`, and `full` smoothing for Vigor Skulls and
  weapon-upgrade materials. Full orders tiers by logical progression; Semi
  preserves a broad early-to-late curve with local variation.
- Matched the default upgrade pool to vanilla totals: one normal +10 weapon
  set (6 Small, 7 Regular, 20 Large, and 1 Chunk), 20 Saintly Quintessences,
  and 3 Antediluvian Chisels.
- Moved pickup detection to the reflected pickup serialization GUID and
  suppresses the vanilla inventory mutation before emitting a check.
- Displays the generated placement for retained safe-mode key/quest checks
  instead of presenting their underlying vanilla safety object as the result.
- Added thirteen common consumable filler items for substantially more varied
  local placements.
- Fixed save-slot recovery by capturing `LoadGame`'s actual slot index and by
  safely selecting a clearly newest primary save when no hint is available.
- Updated the Windows launcher to retain the full-game Steam entitlement and
  avoid the Free Friend's Pass identity.
- Added double-clickable guided Windows install/start/uninstall/diagnostic
  wrappers, ZIP and folder pickers, temporary extraction cleanup, and
  process-local PowerShell execution-policy handling.
- Rewrote installation documentation with an explicit RE-UE4SS download,
  Steam folder discovery, generic paths, expected file layout, and recovery
  troubleshooting.
- Simplified release assets to the APWorld, two complete platform packages,
  and guided Windows installer; redundant checksum and standalone-mod archives
  are no longer produced.
- Existing 0.1.x rooms are intentionally incompatible; generate a new
  multiworld with the 0.2.0 APWorld to receive the expanded location table.

## 0.1.1 - 2026-08-01

README tweaks and repository settings.

## 0.1.0 - 2026-08-01

Initial development release.
