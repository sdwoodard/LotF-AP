from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld

from .data import GAME
from .options import option_groups, option_presets


class LordsOfTheFallenWebWorld(WebWorld):
    game = GAME
    theme = "stone"
    rich_text_options_doc = True
    option_groups = option_groups
    options_presets = option_presets
    tutorials = [
        Tutorial(
            "Multiworld Setup Guide",
            "A guide to installing and playing Lords of the Fallen with Archipelago.",
            "English",
            "setup_en.md",
            "setup/en",
            ["LotF Archipelago contributors"],
        ),
        Tutorial(
            "Game and Randomizer Information",
            "An explanation of checks, items, goals, and safety limitations.",
            "English",
            "info_en.md",
            "info/en",
            ["LotF Archipelago contributors"],
        ),
    ]

