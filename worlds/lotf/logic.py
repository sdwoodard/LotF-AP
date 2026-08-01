"""Shared route logic used by generation and the standalone client."""

from __future__ import annotations

from collections.abc import Collection

from .data import ITEM_BY_NAME, REGION_CONNECTIONS


def requirement_is_active(
    requirement: str | None,
    *,
    shuffle_key_items: bool,
    shuffle_quest_items: bool,
) -> bool:
    if requirement is None:
        return False
    category = ITEM_BY_NAME[requirement].category
    if category == "key":
        return shuffle_key_items
    if category == "quest":
        return shuffle_quest_items
    raise ValueError(f"Unsupported route requirement category for {requirement!r}: {category}")


def reachable_regions(
    received_items: Collection[str],
    *,
    shuffle_key_items: bool,
    shuffle_quest_items: bool,
) -> set[str]:
    """Recreate the APWorld's region closure for the client's `/logic` command."""
    reached = {"Menu"}
    changed = True
    while changed:
        changed = False
        for source, target, requirement in REGION_CONNECTIONS:
            if source not in reached or target in reached:
                continue
            if requirement_is_active(
                requirement,
                shuffle_key_items=shuffle_key_items,
                shuffle_quest_items=shuffle_quest_items,
            ) and requirement not in received_items:
                continue
            reached.add(target)
            changed = True
    return reached
