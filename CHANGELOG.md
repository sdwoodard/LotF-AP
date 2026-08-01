# Changelog

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
