# Lords of the Fallen Randomizer Information

This world uses the retail game's persistent pickup GUIDs as stable checks.
The pool includes 597 eligible pre-placed physical pickups, mapped
traversal/quest objects, major-boss remembrance stigmas, a curated world-stigma
set, boss remembrances, upgrade materials, and common consumable filler. The
tutorial Throwing Stone is deliberately kept vanilla so hanging-corpse items
are always accessible.

The region graph follows the major Axiom routes from the Defiled Sepulchre to
Skyrest, Fen/Calrath, Fief, Manse/Abbey/Empyrean, Bramis Castle, and Mother's
Lull. When key or quest shuffle is disabled, the corresponding rule is also
disabled so Archipelago logic matches the vanilla route.

All 597 physical pickup GUIDs are resolved to their cooked gameplay sublevels
and assigned to explicit base or keyed subregions. This prevents advancement
from being placed behind the same key needed to reach it. Generation and the
client's `/logic` command share this exact graph.

Advancement classification follows check access: every advancement item opens
at least one region or individual check. Quest objects that unlock protected
quest rewards are therefore advancement even though those reward locations
are filler-only. This keeps the unlock item reachable without exposing
progression to an NPC quest.

Vigor Skull and weapon-upgrade smoothing can be disabled, broadly smoothed, or
fully ordered. The strongest mode places smaller tiers earlier and larger
tiers later according to logical spheres and approximate area order; the
middle mode adds variation within nearby portions of that curve.

`any_ending` completes after the credits callback for any ending route.
`all_bosses` requires the ten route-stable remembrance stigmas and excludes
ending-exclusive and NPC-quest encounters so player choices cannot lock the
goal.

Quest-object, known missable, and ending-exclusive checks are permanently
filler-only or may be removed. The fixed 597 physical pickups are never
removed; unsafe rows within that set stay filler-only. Faction-shrine and
Crucible rewards are omitted. No option can place advancement or useful items
at these unsafe sources.

The client command `/logic` (also `/inlogic`) lists unchecked locations the
current received-item state can reach. Results use 30-row pages; a compact area
prefix can be passed as a filter. Each line includes that prefix and a short
description of where or how the check is obtained.

Enemy/destructible drops, shop purchases, faction and Crucible rewards, enemy
placement, entrance randomization, and online features are outside this scope.
