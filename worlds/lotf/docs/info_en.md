# Lords of the Fallen Randomizer Information

This world uses unique cooked item classes as stable checks. The default pool
contains traversal/quest pickups, major-boss remembrance stigmas, a curated
world-stigma set, boss remembrances, Deralium bundles, Saintly Quintessences,
Antediluvian Chisels, and vigor filler.

The region graph follows the major Axiom routes from the Defiled Sepulchre to
Skyrest, Fen/Calrath, Fief, Manse/Abbey/Empyrean, Bramis Castle, and Mother's
Lull. When key or quest shuffle is disabled, the corresponding rule is also
disabled so Archipelago logic matches the vanilla route.

`any_ending` completes after the credits callback for any ending route.
`all_bosses` requires the ten route-stable remembrance stigmas and excludes
ending-exclusive and NPC-quest encounters so player choices cannot lock the
goal.

Quest-object, known missable, and ending-exclusive checks are permanently
filler-only or may be removed. Faction-shrine and Crucible rewards are omitted.
No option can place advancement or useful items at these unsafe sources.

The client command `/logic` (also `/inlogic`) lists unchecked locations the
current received-item state can reach. Each line uses a compact area prefix and
a short description of where or how the check is obtained.

Ordinary duplicated pickups, all weapon/armor locations, enemy placement,
entrance randomization, and online features are outside the 0.1 scope.
