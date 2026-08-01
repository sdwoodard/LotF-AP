"""Static data shared by generation and the client.

Asset paths were derived from the IoStore directory index shipped with Steam
Steam build 24429019. Paths deliberately use Unreal object notation instead of file
system paths so the UE4SS bridge can resolve them at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag

GAME = "Lords of the Fallen"
BASE_ID = 2_023_100_000


class Scope(IntFlag):
    CORE = 1
    QUEST = 2
    BOSS = 4
    STIGMA = 8


@dataclass(frozen=True)
class ItemData:
    name: str
    asset: str | None
    category: str
    progression: bool = False
    useful: bool = False
    quantity: int = 1


@dataclass(frozen=True)
class LocationData:
    name: str
    region: str
    marker: str
    scope: Scope
    missable: bool = False
    suppress_group: str | None = None
    source: str | None = None


def asset(path: str) -> str:
    """Turn a cooked /Game path into a generated-class object path."""
    leaf = path.rsplit("/", 1)[-1]
    return f"{path}.{leaf}_C"


ITEM_ROOT = "/Game/Blueprints/Data/Equipment/Items"


def item_asset(relative: str) -> str:
    return asset(f"{ITEM_ROOT}/{relative}")


# Internal asset labels are used where a retail display-name mapping has not
# been verified.  Keeping the internal label visible is preferable to silently
# granting the wrong object after a game update.
ITEMS: tuple[ItemData, ...] = (
    ItemData("Pilgrim's Perch Key", item_asset("Keys/ITM_KEY_Cliffside_TrainingKey_ItemData"), "key", True),
    ItemData("Skyrest Bridge Key", item_asset("Keys/ITM_KEY_SkywalkBridge_FidelisKey_ItemData"), "key", useful=True),
    ItemData("Fief Key", item_asset("Keys/ITM_KEY_Grove_FrozenForestKey_ItemData"), "key", True),
    ItemData("Sunless Skein Key", item_asset("Keys/ITM_KEY_Mines_FidelitasKey_ItemData"), "key", useful=True),
    ItemData("Drainage Control Key", item_asset("Keys/ITM_KEY_MinesLowerCity_TowerKey_ItemData"), "key", True),
    ItemData("Abbot Vernoff's Key", item_asset("Keys/ITM_KEY_Monastery_ManseAbbotKey_ItemData"), "key", True),
    ItemData("Tancred's Key", item_asset("Keys/ITM_KEY_ChastenerRoom_TowerKey_ItemData"), "key", useful=True),
    ItemData("Bramis Castle Key", item_asset("Keys/ITM_KEY_HighSee_HugeDoorKey_ItemData"), "key", useful=True),
    ItemData("Gerlinde's Cell Key", item_asset("Keys/ITM_KEY_QuestGerlindeSparky_CellKey_ItemData"), "key", useful=True),
    ItemData("Pilgrim's Perch Elevator Key", item_asset("Keys/ITM_KEY_Cliffside_ElevatorKey_ItemData"), "key", useful=True),
    ItemData("Monastery Kitchen Key", item_asset("Keys/ITM_KEY_Monastery_KitchenKey_ItemData"), "key", useful=True),
    ItemData("Castle Royal Key", item_asset("Keys/ITM_KEY_Castle_KingKey_ItemData"), "key", useful=True),
    ItemData("Rune of Adyr", item_asset("Quest/ITM_QST_RuneOfAdyr"), "quest", True),
    ItemData("Empowered Rune of Adyr", item_asset("Quest/ITM_QST_RuneOfAdyr_Empowered"), "quest", useful=True),
    ItemData("Withered Rune of Adyr", item_asset("Quest/ITM_QST_RuneOfAdyr_Umbralized"), "quest", useful=True),
    ItemData("Flayed Skin", item_asset("Quest/ITM_QST_FlayedPieceOfSkin"), "quest", useful=True),
    ItemData("Umbral-Tinged Flayed Skin", item_asset("Quest/ITM_QST_UmbralTingedPieceOfSkin"), "quest", useful=True),
    ItemData("Umbral Wisp", item_asset("Quest/ITM_QST_UmbralWisp"), "quest", useful=True),
    ItemData("Ancient Umbral Tome", item_asset("Quest/ITM_QST_AncientUmbralTome"), "quest", useful=True),
    ItemData("Andreas's Book of Lineage", item_asset("Quest/ITM_QST_AndreasBookOfLineage"), "quest", useful=True),
    ItemData("Catrin's Pendant", item_asset("Quest/ITM_QST_CatrinPendant"), "quest", useful=True),
    ItemData("Elegant Perfume", item_asset("Quest/ITM_QST_ElegantPerfume"), "quest", useful=True),
    ItemData("Adyr-Worshipper's Saw", item_asset("Quest/ITM_QST_AdyrCultistBrandingIron"), "quest", useful=True),
    ItemData("Partially Charred Letter", item_asset("Quest/ITM_QST_PartiallyCharredLetter"), "quest", useful=True),
    ItemData("Poisoned Chalice", item_asset("Quest/ITM_QST_PoisonedChalice"), "quest", useful=True),
    ItemData("Spurned Progeny Eyeball", item_asset("Quest/ITM_QST_SpurnedProgenyEyeball"), "quest", useful=True),
    ItemData("Dark Crusader's Call", item_asset("Quest/ITM_QST_DarkCrusaderCommunicationDevice"), "quest", useful=True),
    ItemData("Dark Crusader's Wooden Cross", item_asset("Quest/ITM_QST_DarkCrusaderCrossCarvedFromWood"), "quest", useful=True),
    ItemData("Ancient Sentinel Banner", item_asset("Quest/ITM_QST_AncientSentinelBanner_1"), "quest", useful=True),
    ItemData("Tattered Sentinel Banner", item_asset("Quest/ITM_QST_AncientSentinelBanner_2"), "quest", useful=True),
    ItemData("Restored Sentinel Banner", item_asset("Quest/ITM_QST_RestoredSentinelBanner"), "quest", useful=True),
    ItemData("Rune Tablet: Cracked", item_asset("Quest/ITM_UPG_RuneSmithingCrystal_01"), "quest", useful=True),
    ItemData("Rune Tablet: Chipped", item_asset("Quest/ITM_UPG_RuneSmithingCrystal_02"), "quest", useful=True),
    ItemData("Rune Tablet", item_asset("Quest/ITM_UPG_RuneSmithingCrystal_03"), "quest", useful=True),
    ItemData("Saintly Quintessence", item_asset("UpgradeMaterials/ITM_UPG_HealthPotionUpgrade"), "upgrade", useful=True),
    ItemData("Antediluvian Chisel", item_asset("UpgradeMaterials/ITM_UPG_LanternUpgrade"), "upgrade", useful=True),
    ItemData("Small Deralium Fragment", item_asset("UpgradeMaterials/ITM_UPG_WeaponUpgrade_01"), "upgrade", useful=True, quantity=3),
    ItemData("Regular Deralium Nugget", item_asset("UpgradeMaterials/ITM_UPG_WeaponUpgrade_02"), "upgrade", useful=True, quantity=2),
    ItemData("Large Deralium Shard", item_asset("UpgradeMaterials/ITM_UPG_WeaponUpgrade_03"), "upgrade", useful=True),
    ItemData("Deralium Chunk", item_asset("UpgradeMaterials/ITM_UPG_WeaponUpgrade_04"), "upgrade", useful=True),
    ItemData("Rebirth Chrysalis", item_asset("UpgradeMaterials/ITM_UPG_CharacterResetCurrency"), "useful", useful=True),
    ItemData("Remembrance of Pieta", item_asset("Remnants/ITM_UTI_Remnant_LightPieta"), "remembrance", useful=True),
    ItemData("Remembrance of the Congregator", item_asset("Remnants/ITM_UTI_Remnant_Boglord"), "remembrance", useful=True),
    ItemData("Remembrance of the Hushed Saint", item_asset("Remnants/ITM_UTI_Remnant_SwampKnight"), "remembrance", useful=True),
    ItemData("Remembrance of the Spurned Progeny", item_asset("Remnants/ITM_UTI_Remnant_FireGiant"), "remembrance", useful=True),
    ItemData("Remembrance of the Hollow Crow", item_asset("Remnants/ITM_UTI_Remnant_Facepoach"), "remembrance", useful=True),
    ItemData("Remembrance of Tancred", item_asset("Remnants/ITM_UTI_Remnant_Chastener"), "remembrance", useful=True),
    ItemData("Remembrance of Judge Cleric", item_asset("Remnants/ITM_UTI_Remnant_Abbess"), "remembrance", useful=True),
    ItemData("Remembrance of the Lightreaper", item_asset("Remnants/ITM_UTI_Remnant_LampHunter"), "remembrance", useful=True),
    ItemData("Remembrance of the Sundered Monarch", item_asset("Remnants/ITM_UTI_Remnant_FatherOfMisery"), "remembrance", useful=True),
    ItemData("Remembrance of Adyr", item_asset("Remnants/ITM_UTI_Remnant_TrueAdyr"), "remembrance", useful=True),
    ItemData("Remembrance of Elianne", item_asset("Remnants/ITM_UTI_Remnant_DarkPieta"), "remembrance", useful=True),
    ItemData("Remembrance of the Unbroken Promise", item_asset("Remnants/ITM_UTI_Remnant_Fidelitas"), "remembrance", useful=True),
    ItemData("Vigor Cache", item_asset("Usables/VigorStones/ITM_CON_VigorStone_03"), "filler", quantity=2),
)


def marker(relative: str) -> str:
    return item_asset(relative).rsplit("/", 1)[-1]


LOCATIONS: tuple[LocationData, ...] = (
    # Unique progression and quest pickups.  The marker is the UItemData class
    # observed by the game bridge, not a memory offset or version-fragile GUID.
    LocationData("Redcopse - Flayed Skin", "Abandoned Redcopse", marker("Quest/ITM_QST_FlayedPieceOfSkin"), Scope.CORE, suppress_group="quest"),
    LocationData("Skyrest - Andreas's Book of Lineage", "Skyrest Bridge", marker("Quest/ITM_QST_AndreasBookOfLineage"), Scope.QUEST, True, "quest"),
    LocationData("Skyrest - Fief Key", "Skyrest Bridge", marker("Keys/ITM_KEY_Grove_FrozenForestKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Skyrest - Pilgrim's Perch Key", "Skyrest Bridge", marker("Keys/ITM_KEY_Cliffside_TrainingKey_ItemData"), Scope.CORE, False, "key", "shop"),
    LocationData("Skyrest - Skyrest Bridge Key", "Skyrest Bridge", marker("Keys/ITM_KEY_SkywalkBridge_FidelisKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Pilgrim's Perch - Gerlinde's Cell Key", "Pilgrim's Perch", marker("Keys/ITM_KEY_QuestGerlindeSparky_CellKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Pilgrim's Perch - Elevator Key", "Pilgrim's Perch", marker("Keys/ITM_KEY_Cliffside_ElevatorKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Forsaken Fen - Dark Crusader's Call", "Forsaken Fen", marker("Quest/ITM_QST_DarkCrusaderCommunicationDevice"), Scope.QUEST, False, "quest"),
    LocationData("Forsaken Fen - Dark Crusader's Wooden Cross", "Forsaken Fen", marker("Quest/ITM_QST_DarkCrusaderCrossCarvedFromWood"), Scope.QUEST, False, "quest"),
    LocationData("Fitzroy's Gorge - Catrin's Pendant", "Fitzroy's Gorge", marker("Quest/ITM_QST_CatrinPendant"), Scope.QUEST, False, "quest"),
    LocationData("Lower Calrath - Adyr-Worshipper's Saw", "Lower Calrath", marker("Quest/ITM_QST_AdyrCultistBrandingIron"), Scope.QUEST, False, "quest"),
    LocationData("Lower Calrath - Sunless Skein Key", "Lower Calrath", marker("Keys/ITM_KEY_Mines_FidelitasKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Sunless Skein - Drainage Control Key", "Sunless Skein", marker("Keys/ITM_KEY_MinesLowerCity_TowerKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Sunless Skein - Rune Tablet: Cracked", "Sunless Skein", marker("Quest/ITM_UPG_RuneSmithingCrystal_01"), Scope.CORE, False, "quest"),
    LocationData("Cistern - Rune Tablet: Chipped", "Cistern", marker("Quest/ITM_UPG_RuneSmithingCrystal_02"), Scope.CORE, False, "quest"),
    LocationData("Tower of Penance - Rune Tablet", "Tower of Penance", marker("Quest/ITM_UPG_RuneSmithingCrystal_03"), Scope.CORE, False, "quest"),
    LocationData("Fief - Partially Charred Letter", "Fief of the Chill Curse", marker("Quest/ITM_QST_PartiallyCharredLetter"), Scope.QUEST, False, "quest"),
    LocationData("Fief - Dark Crusader's Flayed Skin", "Fief of the Chill Curse", marker("Quest/ITM_QST_UmbralTingedPieceOfSkin"), Scope.QUEST, False, "quest"),
    LocationData("Manse - Abbot Vernoff's Key", "Manse of the Hallowed Brothers", marker("Keys/ITM_KEY_Monastery_ManseAbbotKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Manse - Monastery Kitchen Key", "Manse of the Hallowed Brothers", marker("Keys/ITM_KEY_Monastery_KitchenKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Manse - Poisoned Chalice", "Manse of the Hallowed Brothers", marker("Quest/ITM_QST_PoisonedChalice"), Scope.QUEST, True, "quest"),
    LocationData("Tower of Penance - Tancred's Key", "Tower of Penance", marker("Keys/ITM_KEY_ChastenerRoom_TowerKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Abbey - Tattered Sentinel Banner", "Abbey of the Hallowed Sisters", marker("Quest/ITM_QST_AncientSentinelBanner_2"), Scope.QUEST, False, "quest"),
    LocationData("Abbey - Restored Sentinel Banner", "Abbey of the Hallowed Sisters", marker("Quest/ITM_QST_RestoredSentinelBanner"), Scope.QUEST, True, "quest"),
    LocationData("Empyrean - Monastery Royal Key", "The Empyrean", marker("Keys/ITM_KEY_Castle_KingKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Upper Calrath - Bramis Castle Key", "Upper Calrath", marker("Keys/ITM_KEY_HighSee_HugeDoorKey_ItemData"), Scope.CORE, False, "key"),
    LocationData("Upper Calrath - Elegant Perfume", "Upper Calrath", marker("Quest/ITM_QST_ElegantPerfume"), Scope.QUEST, True, "quest"),
    LocationData("Upper Calrath - Rune of Adyr", "Upper Calrath", marker("Quest/ITM_QST_RuneOfAdyr"), Scope.CORE, False, "quest"),
    LocationData("Bramis Castle - Empowered Rune of Adyr", "Bramis Castle", marker("Quest/ITM_QST_RuneOfAdyr_Empowered"), Scope.QUEST, True, "quest"),
    LocationData("Mother's Lull - Withered Rune of Adyr", "Mother's Lull", marker("Quest/ITM_QST_RuneOfAdyr_Umbralized"), Scope.QUEST, True, "quest"),
    LocationData("Mother's Lull - Umbral Wisp", "Mother's Lull", marker("Quest/ITM_QST_UmbralWisp"), Scope.QUEST, True, "quest"),
    LocationData("Mother's Lull - Ancient Umbral Tome", "Mother's Lull", marker("Quest/ITM_QST_AncientUmbralTome"), Scope.QUEST, True, "quest"),
    LocationData("Spurned Progeny - Eyeball", "Lower Calrath", marker("Quest/ITM_QST_SpurnedProgenyEyeball"), Scope.QUEST, False, "quest"),
    # Boss remembrance stigmas are explicit checks after the player soulflays
    # them.  This avoids relying on boss HP offsets or actor instance GUIDs.
    LocationData("Stigma - Pieta", "Skyrest Bridge", marker("Stigmas/Boss/ITM_STI_Boss_PietaLight"), Scope.BOSS),
    LocationData("Stigma - Congregator of Flesh", "Pilgrim's Perch", marker("Stigmas/Boss/ITM_STI_Boss_BogLord"), Scope.BOSS),
    LocationData("Stigma - Hushed Saint", "Forsaken Fen", marker("Stigmas/Boss/ITM_STI_Boss_SwampKnight"), Scope.BOSS),
    LocationData("Stigma - Spurned Progeny", "Lower Calrath", marker("Stigmas/Boss/ITM_STI_Boss_FireGiant"), Scope.BOSS),
    LocationData("Stigma - Hollow Crow", "Fief of the Chill Curse", marker("Stigmas/Boss/ITM_STI_Boss_Facepoach"), Scope.BOSS),
    LocationData("Stigma - Tancred and Reinhold", "Tower of Penance", marker("Stigmas/Boss/ITM_STI_Boss_Chastener"), Scope.BOSS),
    LocationData("Stigma - Judge Cleric", "The Empyrean", marker("Stigmas/Boss/ITM_STI_Boss_Abbess"), Scope.BOSS),
    LocationData("Stigma - Lightreaper", "Upper Calrath", marker("Stigmas/Boss/ITM_STI_Boss_LampHunter"), Scope.BOSS),
    LocationData("Stigma - Sundered Monarch", "Bramis Castle", marker("Stigmas/Boss/ITM_STI_Boss_FatherOfMisery"), Scope.BOSS),
    LocationData("Stigma - Unbroken Promise", "Revelation Depths", marker("Stigmas/Boss/ITM_STI_Boss_Fidelitas"), Scope.BOSS),
    LocationData("Stigma - Elianne the Starved", "Mother's Lull", marker("Stigmas/Boss/ITM_STI_Boss_PietaDark"), Scope.BOSS, True),
    LocationData("Stigma - Adyr", "Rhogar Realm", marker("Stigmas/Boss/ITM_STI_Boss_TrueAdyr"), Scope.BOSS, True),
    # A compact selection of world stigmas gives optional, non-progression
    # checks without making the first release depend on every map instance.
    LocationData("World Stigma - Redcopse I", "Abandoned Redcopse", marker("Stigmas/World/ITM_STI_World_Abandoned_Redcopse_01"), Scope.STIGMA),
    LocationData("World Stigma - Pilgrim's Perch I", "Pilgrim's Perch", marker("Stigmas/World/ITM_STI_World_Pilgrims_Perch_01"), Scope.STIGMA),
    LocationData("World Stigma - Forsaken Fen I", "Forsaken Fen", marker("Stigmas/World/ITM_STI_World_Forsaken_Fen_01"), Scope.STIGMA),
    LocationData("World Stigma - Fitzroy's Gorge I", "Fitzroy's Gorge", marker("Stigmas/World/ITM_STI_World_Fitzroys_Gorge_01"), Scope.STIGMA),
    LocationData("World Stigma - Lower Calrath I", "Lower Calrath", marker("Stigmas/World/ITM_STI_World_Lower_Calrath_01"), Scope.STIGMA),
    LocationData("World Stigma - Sunless Skein I", "Sunless Skein", marker("Stigmas/World/ITM_STI_World_Sunless_Skein_02"), Scope.STIGMA),
    LocationData("World Stigma - Fief I", "Fief of the Chill Curse", marker("Stigmas/World/ITM_STI_World_Fief_01"), Scope.STIGMA),
    LocationData("World Stigma - Manse I", "Manse of the Hallowed Brothers", marker("Stigmas/World/ITM_STI_World_Manse_01"), Scope.STIGMA),
    LocationData("World Stigma - Tower of Penance I", "Tower of Penance", marker("Stigmas/World/ITM_STI_World_Tower_of_Penance_01"), Scope.STIGMA),
    LocationData("World Stigma - Abbey I", "Abbey of the Hallowed Sisters", marker("Stigmas/World/ITM_STI_World_Abbey_01"), Scope.STIGMA),
    LocationData("World Stigma - Empyrean I", "The Empyrean", marker("Stigmas/World/ITM_STI_World_Empyrean_01"), Scope.STIGMA),
    LocationData("World Stigma - Upper Calrath I", "Upper Calrath", marker("Stigmas/World/ITM_STI_World_Upper_Calrath_01"), Scope.STIGMA),
    LocationData("World Stigma - Bramis Castle I", "Bramis Castle", marker("Stigmas/World/ITM_STI_World_Bramis_Castle_01"), Scope.STIGMA),
)


ITEM_BY_NAME = {entry.name: entry for entry in ITEMS}
LOCATION_BY_NAME = {entry.name: entry for entry in LOCATIONS}
ITEM_NAME_TO_ID = {entry.name: BASE_ID + index for index, entry in enumerate(ITEMS, 1)}
LOCATION_NAME_TO_ID = {entry.name: BASE_ID + 10_000 + index for index, entry in enumerate(LOCATIONS, 1)}

assert len(ITEM_BY_NAME) == len(ITEMS), "duplicate item name"
assert len(LOCATION_BY_NAME) == len(LOCATIONS), "duplicate location name"
assert len({entry.marker for entry in LOCATIONS}) == len(LOCATIONS), "duplicate marker"


REGION_CONNECTIONS: tuple[tuple[str, str, str | None], ...] = (
    ("Menu", "Defiled Sepulchre", None),
    ("Defiled Sepulchre", "Abandoned Redcopse", None),
    ("Abandoned Redcopse", "Skyrest Bridge", None),
    ("Skyrest Bridge", "Pilgrim's Perch", None),
    ("Pilgrim's Perch", "Forsaken Fen", None),
    ("Forsaken Fen", "Fitzroy's Gorge", None),
    ("Fitzroy's Gorge", "Lower Calrath", None),
    ("Lower Calrath", "Sunless Skein", None),
    ("Sunless Skein", "Cistern", None),
    ("Cistern", "Revelation Depths", "Drainage Control Key"),
    ("Skyrest Bridge", "Fief of the Chill Curse", "Fief Key"),
    ("Skyrest Bridge", "Path of Devotion", None),
    ("Path of Devotion", "Manse of the Hallowed Brothers", "Pilgrim's Perch Key"),
    ("Manse of the Hallowed Brothers", "Tower of Penance", None),
    ("Manse of the Hallowed Brothers", "Abbey of the Hallowed Sisters", "Abbot Vernoff's Key"),
    ("Abbey of the Hallowed Sisters", "The Empyrean", None),
    ("Cistern", "Upper Calrath", None),
    ("Upper Calrath", "Bramis Castle", "Rune of Adyr"),
    ("Bramis Castle", "Rhogar Realm", None),
    ("Revelation Depths", "Mother's Lull", None),
)


# Compact area codes are shown by the client before each check.
REGION_PREFIXES: dict[str, str] = {
    "Defiled Sepulchre": "DS",
    "Abandoned Redcopse": "AR",
    "Skyrest Bridge": "SB",
    "Pilgrim's Perch": "PP",
    "Forsaken Fen": "FF",
    "Fitzroy's Gorge": "FG",
    "Lower Calrath": "LC",
    "Sunless Skein": "SS",
    "Cistern": "CI",
    "Revelation Depths": "RD",
    "Fief of the Chill Curse": "FI",
    "Path of Devotion": "PD",
    "Manse of the Hallowed Brothers": "MH",
    "Tower of Penance": "TP",
    "Abbey of the Hallowed Sisters": "AH",
    "The Empyrean": "EM",
    "Upper Calrath": "UC",
    "Bramis Castle": "BC",
    "Rhogar Realm": "RR",
    "Mother's Lull": "ML",
}


LOCATION_DESCRIPTIONS: dict[str, str] = {
    "Redcopse - Flayed Skin": "Unique Umbral pickup near the start of Abandoned Redcopse.",
    "Skyrest - Andreas's Book of Lineage": "Received during Andreas of Ebb's quest at Skyrest Bridge.",
    "Skyrest - Fief Key": "Received from Andreas of Ebb at Skyrest Bridge.",
    "Skyrest - Pilgrim's Perch Key": "Bought from Stomund or left behind when he departs.",
    "Skyrest - Skyrest Bridge Key": "Umbral pickup beneath Skyrest Bridge.",
    "Pilgrim's Perch - Gerlinde's Cell Key": "Found near Gerlinde's prison cell in Pilgrim's Perch.",
    "Pilgrim's Perch - Elevator Key": "Found near the elevator shortcut in Pilgrim's Perch.",
    "Forsaken Fen - Dark Crusader's Call": "Obtained during Paladin Isaac's quest in Forsaken Fen.",
    "Forsaken Fen - Dark Crusader's Wooden Cross": "Obtained during Paladin Isaac's quest in Forsaken Fen.",
    "Fitzroy's Gorge - Catrin's Pendant": "Obtained during Byron and Winterberry's quest in Fitzroy's Gorge.",
    "Lower Calrath - Adyr-Worshipper's Saw": "Obtained during Damarose's quest in Lower Calrath.",
    "Lower Calrath - Sunless Skein Key": "Found in the Sunless Skein mine.",
    "Sunless Skein - Drainage Control Key": "Dropped by Skinstealer in the Cistern.",
    "Sunless Skein - Rune Tablet: Cracked": "Found in the Sunless Skein mine.",
    "Cistern - Rune Tablet: Chipped": "Found in the Cistern.",
    "Tower of Penance - Rune Tablet": "Found in the Tower of Penance.",
    "Fief - Partially Charred Letter": "Obtained during Drustan's quest in the Fief.",
    "Fief - Dark Crusader's Flayed Skin": "Found during Paladin Isaac's quest in the Fief.",
    "Manse - Abbot Vernoff's Key": "Found in the Manse of the Hallowed Brothers.",
    "Manse - Monastery Kitchen Key": "Found in the Manse kitchen area.",
    "Manse - Poisoned Chalice": "Obtained during Exacter Dunmire's quest in the Manse.",
    "Tower of Penance - Tancred's Key": "Obtained after Tancred and Reinhold in the Tower of Penance.",
    "Abbey - Tattered Sentinel Banner": "Obtained during Stomund's quest in the Abbey.",
    "Abbey - Restored Sentinel Banner": "Received during Stomund's quest in the Abbey.",
    "Empyrean - Monastery Royal Key": "Unique pickup in The Empyrean.",
    "Upper Calrath - Bramis Castle Key": "Unique pickup in Upper Calrath.",
    "Upper Calrath - Elegant Perfume": "Obtained during the Tortured Prisoner's quest in Upper Calrath.",
    "Upper Calrath - Rune of Adyr": "Found in the Abbey or dropped by the Iron Wayfarer, depending on quest state.",
    "Bramis Castle - Empowered Rune of Adyr": "Obtained during the Inferno-ending sequence in Bramis Castle.",
    "Mother's Lull - Withered Rune of Adyr": "Obtained during the Umbral-ending sequence in Mother's Lull.",
    "Mother's Lull - Umbral Wisp": "Obtained during the Dunmire and Molhu quest sequences in Mother's Lull.",
    "Mother's Lull - Ancient Umbral Tome": "Obtained during Exacter Dunmire's quest in Mother's Lull.",
    "Spurned Progeny - Eyeball": "Obtained during Damarose's quest after defeating the Spurned Progeny.",
}


ENDING_LOCKED_LOCATIONS = frozenset({
    "Stigma - Adyr",
    "Stigma - Elianne the Starved",
})

GRINDY_LOCATION_SOURCES = frozenset({"faction_reward", "crucible"})

ALL_BOSSES_GOAL_LOCATIONS: tuple[str, ...] = (
    "Stigma - Pieta",
    "Stigma - Congregator of Flesh",
    "Stigma - Hushed Saint",
    "Stigma - Spurned Progeny",
    "Stigma - Hollow Crow",
    "Stigma - Unbroken Promise",
    "Stigma - Tancred and Reinhold",
    "Stigma - Judge Cleric",
    "Stigma - Lightreaper",
    "Stigma - Sundered Monarch",
)


def location_source(entry: LocationData) -> str:
    if entry.source:
        return entry.source
    if entry.scope & Scope.BOSS:
        return "boss"
    if entry.scope == Scope.STIGMA:
        return "world_stigma"
    if entry.suppress_group == "quest":
        return "quest"
    if entry.suppress_group == "key":
        return "key"
    return "world"


def location_is_unsafe(entry: LocationData) -> bool:
    """Return whether a check must never receive advancement or useful items."""
    return (
        entry.missable
        or entry.suppress_group == "quest"
        or entry.name in ENDING_LOCKED_LOCATIONS
        or location_source(entry) in GRINDY_LOCATION_SOURCES
    )


def location_description(entry: LocationData) -> str:
    if entry.name in LOCATION_DESCRIPTIONS:
        return LOCATION_DESCRIPTIONS[entry.name]
    if entry.scope & Scope.BOSS:
        boss_name = entry.name.removeprefix("Stigma - ")
        return f"Soulflay the remembrance stigma after defeating {boss_name}."
    if entry.scope == Scope.STIGMA:
        return f"Soulflay the curated Umbral world stigma in {entry.region}."
    return f"Unique pickup in {entry.region}."
