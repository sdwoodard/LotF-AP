import random
from unittest import TestCase

from ..options import ItemSmoothing
from ..smoothing import (
    SMOOTHING_REGION_ORDER,
    VIGOR_SKULL_RANKS,
    WEAPON_UPGRADE_RANKS,
    order_for_smoothing,
)
from ..data import REGION_CONNECTIONS


class TestItemSmoothing(TestCase):
    def test_off_preserves_order(self) -> None:
        names = ["Deralium Chunk", "Small Deralium Fragment", "Large Deralium Shard"]
        self.assertEqual(
            names,
            order_for_smoothing(
                names,
                WEAPON_UPGRADE_RANKS,
                ItemSmoothing.option_off,
                random.Random(1),
                name=lambda value: value,
            ),
        )

    def test_full_is_monotonic(self) -> None:
        names = list(reversed(tuple(VIGOR_SKULL_RANKS))) * 4
        result = order_for_smoothing(
            names,
            VIGOR_SKULL_RANKS,
            ItemSmoothing.option_full,
            random.Random(2),
            name=lambda value: value,
        )
        ranks = [VIGOR_SKULL_RANKS[name] for name in result]
        self.assertEqual(sorted(ranks), ranks)

    def test_semi_randomizes_only_within_nearby_bands(self) -> None:
        names = [name for name in VIGOR_SKULL_RANKS for _ in range(12)]
        result = order_for_smoothing(
            list(reversed(names)),
            VIGOR_SKULL_RANKS,
            ItemSmoothing.option_semi,
            random.Random(3),
            name=lambda value: value,
        )
        ranks = [VIGOR_SKULL_RANKS[name] for name in result]
        band_size = max(3, (len(ranks) + 7) // 8)
        bands = [ranks[start : start + band_size] for start in range(0, len(ranks), band_size)]
        self.assertTrue(
            all(max(left) <= min(right) for left, right in zip(bands, bands[1:]))
        )
        self.assertNotEqual(sorted(ranks), ranks)
        self.assertLessEqual(
            sum(ranks[: len(ranks) // 4]),
            sum(ranks[-len(ranks) // 4 :]),
        )

    def test_area_order_covers_every_logic_region(self) -> None:
        regions = {name for edge in REGION_CONNECTIONS for name in edge[:2]}
        self.assertEqual(regions, set(SMOOTHING_REGION_ORDER))
