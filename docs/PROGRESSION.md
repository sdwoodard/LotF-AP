# Progression and location-safety policy

Version 0.1.0 treats an item as Archipelago advancement only when the APWorld's
implemented region graph directly requires it. An item being rare, unique,
useful for a build, or capable of expanding a merchant inventory is not enough.

## Advancement items

| Item | AP route it opens | Why it is safe to require |
| --- | --- | --- |
| Pilgrim's Perch Key | Path of Devotion and the Manse route from Pilgrim's Perch | When shuffled, its vanilla sale/drop is suppressed and Archipelago places the replacement only at a safe reachable check. |
| Fief Key | Fief of the Chill Curse from Skyrest/Redcopse | When shuffled, its Andreas pickup is suppressed and the replacement is subject to normal reachability fill. |
| Drainage Control Key | Revelation Depths from the Cistern | It is the Skinstealer reward used to reach and drain the lower Cistern route. |
| Abbot Vernoff's Key | Abbey of the Hallowed Sisters and the Empyrean route | It is an unconditional Manse world pickup, not an NPC quest reward. |
| Rune of Adyr | The rooted gate into Bramis Castle | Its observed pickup can move with the Iron Wayfarer state, so its check is conservatively filler-only while the shuffled replacement is placed at a separate safe check. |

These items enter the AP item pool only when their corresponding shuffle option
is enabled. When shuffling is off, the vanilla item remains in place and the
matching AP region rule is disabled.

## Progression chains

Reachability starts at the menu and closes over the region graph in order. An
item never grants access to its target from nowhere: the source region must
already be reachable. The important chained case is Abbot Vernoff's Key. Its
source gate is in the Manse, so a shuffled Pilgrim's Perch Key must first make
the Path of Devotion/Manse route reachable before the Abbot key can help.

The Rune of Adyr gates Bramis Castle from Upper Calrath. In the implemented
graph, Upper Calrath is on the route-stable main path through the Cistern; none
of the other four shuffled requirements gates access to the rooted door. The
Rune therefore does not have an artificial prerequisite, but it still cannot
make Bramis Castle reachable until Upper Calrath itself is reachable. The
`all_bosses` goal separately needs the Fief, Revelation Depths, Abbey/Empyrean,
and Bramis branches, so all five active requirements—and the Pilgrim/Abbot
ordering—are exercised when both shuffle options are enabled.

The generation-matrix test independently removes each active requirement while
granting every other progression item, verifies that the source is reachable
but the target is not, then grants the omitted item and verifies the target.
It also walks the actual filled progression spheres and rejects a seed if a
goal-required item is not obtained before Victory.

## Deliberately not advancement

Every other mapped key and quest object is useful at most. In particular:

- Ancient Umbral Tome, Umbral Wisp, Poisoned Chalice, and other Dunmire objects
  do not gate AP logic. Dunmire moves and eventually dies during his quest.
- Adyr-Worshipper's Saw and the Spurned Progeny Eyeball can expand Damarose's
  inventory, but her availability depends on beacon/ending choices.
- Ancient, Tattered, and Restored Sentinel Banners are tied to Stomund, who
  leaves Skyrest and can die during his quest.
- The three Rune Tablets expand rune/socket services and merchant inventory,
  but the Gerlinde/Sparky decision changes prices, services, and availability.
- Withered and Empowered Runes of Adyr are ending-route objects. They are not
  used as goal markers and are not universal progression for `any_ending`.
- Umbral-Tinged Flayed Skin belongs to Paladin Isaac's optional quest and does
  not actually open Mother's Lull, so it is not an AP route requirement.
- Gerlinde's Cell Key unlocks an important service, but the service is optional
  for completion and therefore classified useful rather than advancement.

No merchant-stock unlock currently meets the project's strict standard for
advancement: the same shopkeeper must remain accessible regardless of player
choices and quest state for the rest of the single playthrough.

## Protected locations

All quest-object checks, all known missable checks, and the Adyr and Elianne
boss checks are hard-protected. They are marked `EXCLUDED` and given an
explicit item rule which rejects advancement and useful items. The
player option may keep these checks as filler-only or remove them; it cannot
make them eligible for progression.

Faction-shrine rewards and Crucible rewards are not in the location table. The
data model reserves `faction_reward` and `crucible` source tags as unsafe, and
tests fail if either source is added to the pool without revisiting this policy.

## `all_bosses` scope

The goal uses ten route-stable remembrance stigma checks: Pieta, Congregator
of Flesh, Hushed Saint, Spurned Progeny, Hollow Crow, Unbroken Promise,
Tancred/Reinhold, Judge Cleric, Lightreaper, and Sundered Monarch.

It excludes Adyr and Elianne because each is ending-exclusive, and every
NPC-quest boss because player decisions can permanently prevent those
encounters. The Unbroken Promise stigma represents the route-stable Harrower
Dervla/Unbroken Promise fight in Revelation Depths.
