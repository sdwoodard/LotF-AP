# Supported game build

Version 0.2.0 was audited against the installed Steam release on 2026-08-01:

- Steam App ID: `1501750`
- Steam build ID: `24429019`
- executable: `LOTF2\Binaries\Win64\LOTF2-Win64-Shipping.exe`
- executable size: `140903936` bytes
- executable SHA-256:
  `B25959F940C0D294A9E3F57B7FCE3E4B727B2C417F63C3B811C7857FCE47A886`
- executable last-written UTC: `2026-08-01T12:49:28Z`
- engine/content layout: Unreal Engine 5.1 IoStore
- internal script module: `/Script/LOTF2`
- full-game Steam App ID: `1501750` (Friend's Pass is `3664720`)
- eligible pre-placed pickup GUIDs: `597`, after excluding the tutorial
  Throwing Stone row `816_Quest_QST_Quest`

The executable does not expose a useful Windows file-version string, so the
diagnostic and validation scripts use SHA-256, byte size, timestamp, reflected
function names, asset names, and cooked paths instead. Steam build ID comes
from `steamapps/appmanifest_1501750.acf`.

The bridge contains no absolute addresses. A future game update can still
rename an asset or alter a reflected function signature. `Test-Repository`
therefore refuses a supplied executable whose hash and size are not recorded
above. Audit the new build and pre-placed-loot map, update this document
deliberately, rerun exact `retoc` validation, and start with key/quest
suppression disabled.
