from dataclasses import dataclass

from Options import (
    Choice,
    DefaultOnToggle,
    ItemsAccessibility,
    OptionGroup,
    PerGameCommonOptions,
    Range,
    Toggle,
)


class Goal(Choice):
    """
    Condition which completes the Archipelago slot.

    Any Ending accepts the credits after any ending route. All Bosses requires
    the ten route-stable remembrance bosses tracked by this integration. It
    deliberately excludes ending-exclusive and NPC-quest bosses.
    """

    display_name = "Goal"
    option_any_ending = 0
    option_all_bosses = 1
    default = option_any_ending


class IncludeQuestLocations(DefaultOnToggle):
    """Include unique NPC-quest and ending-object pickups as checks."""

    display_name = "Include Quest Locations"


class IncludeWorldStigmas(DefaultOnToggle):
    """Include a curated set of non-boss Umbral stigmas as checks."""

    display_name = "Include World Stigmas"


class ShuffleKeyItems(Toggle):
    """
    Put traversal keys into the multiworld and replace their vanilla pickups.

    This requires the game bridge's suppression hook. Leave disabled if the
    client reports that suppression is unavailable for the installed build.
    """

    display_name = "Shuffle Key Items"


class ShuffleQuestItems(Toggle):
    """
    Put unique quest objects into the multiworld and replace their vanilla
    pickups. Quest checks are permanently barred from useful and progression
    placement, but changing or failing an NPC quest may still make the vanilla
    quest itself impossible. Recommended only for experimental seeds.
    """

    display_name = "Shuffle Quest Items"


class LocalKeyItems(DefaultOnToggle):
    """Keep traversal keys in this Lords of the Fallen world."""

    display_name = "Local Key Items"


class EarlyPilgrimsPerchKey(DefaultOnToggle):
    """Place Pilgrim's Perch Key in an early local sphere when shuffled."""

    display_name = "Early Pilgrim's Perch Key"


class EarlyFiefKey(Toggle):
    """Place Fief Key in an early local sphere when shuffled."""

    display_name = "Early Fief Key"


class RemembranceItems(DefaultOnToggle):
    """Add major-boss remembrances to the item pool."""

    display_name = "Remembrance Items"


class WeaponUpgradeItems(Range):
    """Number of Deralium upgrade bundles added before filler."""

    display_name = "Weapon Upgrade Bundles"
    range_start = 0
    range_end = 30
    default = 8


class SanguinarixUpgradeItems(Range):
    """Number of Saintly Quintessences added before filler."""

    display_name = "Sanguinarix Upgrades"
    range_start = 0
    range_end = 20
    default = 5


class LampUpgradeItems(Range):
    """Number of Antediluvian Chisels added before filler."""

    display_name = "Umbral Lamp Upgrades"
    range_start = 0
    range_end = 3
    default = 2


class MissableLocationBehavior(Choice):
    """
    How to handle NPC-quest, ending-dependent, and other unsafe checks.

    Forbid Progression keeps them as filler-only checks. Remove omits them.
    There is intentionally no Allow mode: unsafe checks can never contain an
    advancement or useful item, even through user exclusion/plando settings.
    """

    display_name = "Missable Location Behavior"
    option_forbid_progression = 1
    option_remove = 2
    default = option_forbid_progression


class DeathLink(Choice):
    """Share player deaths with the multiworld."""

    display_name = "Death Link"
    option_off = 0
    option_any_death = 1
    default = option_off


class DeathLinkAmnesty(Range):
    """Number of qualifying local deaths required to send one DeathLink."""

    display_name = "Death Link Amnesty"
    range_start = 1
    range_end = 10
    default = 1


class ItemDeliveryDelay(Range):
    """Milliseconds between game-side item grants."""

    display_name = "Item Delivery Delay"
    range_start = 250
    range_end = 5000
    default = 1000


@dataclass
class LordsOfTheFallenOptions(PerGameCommonOptions):
    accessibility: ItemsAccessibility
    goal: Goal
    include_quest_locations: IncludeQuestLocations
    include_world_stigmas: IncludeWorldStigmas
    shuffle_key_items: ShuffleKeyItems
    shuffle_quest_items: ShuffleQuestItems
    local_key_items: LocalKeyItems
    early_pilgrims_perch_key: EarlyPilgrimsPerchKey
    early_fief_key: EarlyFiefKey
    remembrance_items: RemembranceItems
    weapon_upgrade_items: WeaponUpgradeItems
    sanguinarix_upgrade_items: SanguinarixUpgradeItems
    lamp_upgrade_items: LampUpgradeItems
    missable_location_behavior: MissableLocationBehavior
    death_link: DeathLink
    death_link_amnesty: DeathLinkAmnesty
    item_delivery_delay: ItemDeliveryDelay


option_groups = [
    OptionGroup(
        "Location Pool",
        [IncludeQuestLocations, IncludeWorldStigmas, MissableLocationBehavior],
    ),
    OptionGroup(
        "Item Randomization",
        [
            ShuffleKeyItems,
            ShuffleQuestItems,
            LocalKeyItems,
            EarlyPilgrimsPerchKey,
            EarlyFiefKey,
            RemembranceItems,
            WeaponUpgradeItems,
            SanguinarixUpgradeItems,
            LampUpgradeItems,
        ],
    ),
    OptionGroup("Links", [DeathLink, DeathLinkAmnesty]),
    OptionGroup("Client", [ItemDeliveryDelay]),
]


option_presets = {
    "Safe First Seed": {
        "shuffle_key_items": False,
        "shuffle_quest_items": False,
        "include_quest_locations": True,
        "include_world_stigmas": True,
        "death_link": DeathLink.option_off,
    },
    "Full Multiworld": {
        "shuffle_key_items": True,
        "shuffle_quest_items": True,
        "local_key_items": True,
        "include_quest_locations": True,
        "include_world_stigmas": True,
    },
}
