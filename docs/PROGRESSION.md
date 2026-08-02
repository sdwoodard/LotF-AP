# Progression and location-safety policy

Version 0.2.1 classifies an item as Archipelago advancement only when it
unlocks at least one generated check. This includes both region entrances and
individual quest-reward checks. Being rare, useful for a build, or able to
expand a merchant inventory is not sufficient by itself.

## Advancement items

| Item | Implemented gate | Goal relevance |
| --- | --- | --- |
| Skyrest Bridge Key | Locked crypt and dormitory pickups at Skyrest Bridge | Optional side checks |
| Pilgrim's Perch Key | Belled Rise, then the Path of Devotion and Manse route | `all_bosses` chain |
| Fief Key | Fief of the Chill Curse | `all_bosses` chain |
| Sunless Skein Key | The keyed Lower Calrath/Sunless Skein annex | Optional side checks |
| Drainage Control Key | Cistern to Revelation Depths | `all_bosses` chain |
| Monastery Kitchen Key | Kitchen and interior route through the Manse | `all_bosses` chain |
| Abbot Vernoff's Key | Tower of Penance and Abbey branches from the Manse | `all_bosses` chain |
| Tancred's Key | Post-boss lift and locked-cell pickup | Optional for the AP goals; required by some vanilla ending routes |
| Empyrean Church Key | Empyrean church and Judge Cleric | `all_bosses` chain |
| Royal Key | Royal wing of Bramis Castle and Sundered Monarch | Both goals |
| Rune of Adyr | Upper Calrath to Bramis Castle | Both goals |
| Flayed Skin | Umbral-Tinged Flayed Skin quest check | Optional, protected check |
| Spurned Progeny Eyeball | Elegant Perfume quest check | Optional, protected check |
| Ancient Sentinel Banner | Restored Sentinel Banner quest check | Optional, protected check |
| Tattered Sentinel Banner | Restored Sentinel Banner quest check | Optional, protected check |

Key items enter the AP item pool only when `shuffle_key_items` is enabled. The
Rune and four quest-check requirements enter only when `shuffle_quest_items`
is enabled. With the relevant shuffle off, the vanilla object remains
available and its AP rule is disabled.

The four quest chains above are advancement even though their destination
checks are permanently filler-only. Advancement describes what the item
unlocks; location safety separately controls what may be placed at the
unlocked check. The two banner parts are both required for the restored-banner
check.

## Audited pickup logic

The retail `DA_PrePlacedRandomLootMap` supplies 597 eligible persistent pickup
GUIDs. The 0.2.1 audit resolves every GUID against the cooked gameplay maps in
Steam build 24429019: 597 of 597 resolved across 141 sublevels, with one
reviewed level-instance reference appearing in two Bramis Castle maps. The
checked-in `pickup_sublevels.py` is the reproducible evidence table.

Each physical check has an explicit `logic_region`. The important keyed groups
are:

| Logic group | Physical checks | Required item |
| --- | ---: | --- |
| Pilgrim's Perch - Belled Rise and keyed rooms | 21 | Pilgrim's Perch Key |
| Skyrest Bridge - Locked Crypt | 9 | Skyrest Bridge Key |
| Fief of the Chill Curse | 49 | Fief Key |
| Lower Calrath - Sunless Skein Annex | 9 | Sunless Skein Key |
| Revelation Depths | 51 | Drainage Control Key |
| Manse - Kitchen and Interior | 32 | Pilgrim's Perch Key, then Monastery Kitchen Key |
| Tower of Penance | 19 | Pilgrim's Perch, Kitchen, and Abbot chain |
| Tower locked-cell pickup | 1 | The Tower chain, then Tancred's Key |
| Abbey of the Hallowed Sisters | 30 | Pilgrim's Perch, Kitchen, and Abbot chain |
| The Empyrean - Church | 5 | The Abbey chain, then Empyrean Church Key |
| Bramis Castle - Royal Wing | 36 | Rune of Adyr, then Royal Key |

The Tancred audit is deliberately actor-specific. The ordinary pickups in
`PT_GAM_MainINT` are encountered while descending toward the boss and therefore
remain pre-key. Only retail row `266_PenitentTower_AX_Difficult`, the hand-named
Flickering Flail pickup in the locked cell, is placed after Tancred's Key.

Where a keyed door and pre-door floor share one cooked sublevel, the complete
sublevel is assigned to the later side. This applies to the Blacksmith and
Sanctuary sublevels at Pilgrim's Perch and the Bramis donjon interior. It can
make `/logic` conservatively list a physically reachable pickup one sphere
later, but it cannot falsely advertise an inaccessible check or allow
progression to self-lock inside a keyed room.

An SHA-256 assertion covers every pickup GUID, retail row, cooked map, and
logic-region assignment. Changing the retail table or an assignment without
re-running and reviewing the audit fails import and generation tests instead
of silently weakening logic.

## Progression chains

Reachability is a closure over directed region edges: possessing a key cannot
grant its destination unless the source region is already reachable. This
captures dependencies such as:

```text
Pilgrim's Perch Key
  -> Belled Rise / Manse
  -> Monastery Kitchen Key
  -> Manse interior
  -> Abbot Vernoff's Key
  -> Abbey
  -> Empyrean Church Key
  -> Judge Cleric

Rune of Adyr
  -> Bramis Castle
  -> Royal Key
  -> Royal Wing / Sundered Monarch / ending
```

For `any_ending`, the generator audit proves that active shuffled Rune and
Royal Key placements are reached before Victory. For `all_bosses`, it also
proves the Pilgrim/Manse/Abbey chain, Fief Key, and Drainage Control Key are
reached first. Optional side-section keys and quest-check requirements are
still normal advancement items, so `accessibility: full` keeps their checks
reachable even though they are not part of the shortest goal path.

The generation matrix also tests every active edge independently: it grants all
other advancement items, proves the target remains unreachable without the
selected requirement, grants that requirement, and then proves the target
becomes reachable. Actual filled seeds are walked sphere by sphere; a seed is
rejected if Victory or an advancement item is stranded.

## Deliberately not advancement

All other mapped quest objects and service unlocks are useful at most because
none unlock another check in the 0.2.1 location table:

- Dunmire objects do not gate AP logic because Dunmire moves and eventually
  dies during his quest.
- Damarose and Stomund stock/quest objects depend on beacon or quest choices.
- Rune Tablets affect Gerlinde/Sparky services, whose state depends on the
  player's quest decision.
- Gerlinde's Cell Key unlocks a valuable service but is not needed for either
  goal; it remains useful rather than advancement.
- Withered and Empowered Runes of Adyr belong to ending-specific routes. They
  are protected checks unlocked by the base Rune, not keys to later AP checks.

No merchant-stock unlock meets the strict advancement standard: its merchant
would need to remain accessible regardless of quest and ending choices for the
rest of the playthrough.

## Protected and excluded locations

The starting Throwing Stone is omitted and remains vanilla. Every other one of
the 597 eligible physical pickups is a check. The two retail quest-classified
rows remain in that fixed set but are filler-only.

All quest-object, known missable, and ending-exclusive checks are marked
`EXCLUDED` and have an explicit item rule rejecting both advancement and useful
items. The player option can retain additional unsafe checks as filler-only or
remove them; it cannot make them progression-capable.

Faction-shrine and Crucible rewards are absent from the location table. Their
source tags are reserved as unsafe, and tests fail if either source enters the
pool without an explicit policy review.

## `all_bosses` scope

The goal uses ten route-stable remembrance stigma checks: Pieta, Congregator
of Flesh, Hushed Saint, Spurned Progeny, Hollow Crow, Unbroken Promise,
Tancred/Reinhold, Judge Cleric, Lightreaper, and Sundered Monarch.

Adyr and Elianne are ending-exclusive. NPC-quest bosses are choice-lockable.
Both groups are excluded so the goal remains achievable in one playthrough
regardless of quest and ending decisions.
