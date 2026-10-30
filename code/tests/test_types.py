"""Tests for the core types for Minesweeper games."""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from sweepstakes import types
from sweepstakes.types import (
    FlagResult,
    GameStatus,
    HIDDEN_CLUE,
    Observation,
    RevealResult,
    Rules,
)


def test_rules_stores_fields():
    rules = Rules(width=9, height=8, total_mines=10, max_mines_per_tile=2)

    assert rules.width == 9
    assert rules.height == 8
    assert rules.total_mines == 10
    assert rules.max_mines_per_tile == 2


@pytest.mark.parametrize(
    ("width", "height"), [(0, 5), (5, 0), (-1, 5), (5, -1), (0, 0)]
)
def test_rules_rejects_bad_dimensions(width: int, height: int):
    with pytest.raises(ValueError, match="Dimensions"):
        Rules(width=width, height=height, total_mines=0, max_mines_per_tile=1)


@pytest.mark.parametrize("total_mines", [0, 1, 12])
def test_rules_accepts_mine_counts_in_range(total_mines: int):
    rules = Rules(
        width=3, height=2, total_mines=total_mines, max_mines_per_tile=2
    )

    assert rules.total_mines == total_mines


@pytest.mark.parametrize("total_mines", [-1, 13])
def test_rules_rejects_mine_counts_out_of_range(total_mines: int):
    with pytest.raises(ValueError, match="Total mines"):
        Rules(width=3, height=2, total_mines=total_mines, max_mines_per_tile=2)


@pytest.mark.parametrize("max_mines_per_tile", [0, -1])
def test_rules_rejects_bad_max_mines_per_tile(max_mines_per_tile: int):
    with pytest.raises(ValueError):
        Rules(
            width=3,
            height=2,
            total_mines=1,
            max_mines_per_tile=max_mines_per_tile,
        )


def test_rules_is_frozen():
    rules = Rules(width=3, height=3, total_mines=1, max_mines_per_tile=1)

    with pytest.raises(FrozenInstanceError):
        rules.width = 4  # type: ignore[misc]


def test_rules_compare_and_hash_by_value():
    rules1 = Rules(width=3, height=3, total_mines=1, max_mines_per_tile=1)
    rules2 = Rules(width=3, height=3, total_mines=1, max_mines_per_tile=1)
    rules3 = Rules(width=3, height=3, total_mines=2, max_mines_per_tile=1)

    assert rules1 == rules2
    assert hash(rules1) == hash(rules2)
    assert rules1 != rules3


def test_observation_is_frozen():
    obs = Observation(
        rules=Rules(width=1, height=1, total_mines=0, max_mines_per_tile=1),
        clues=np.full((1, 1), HIDDEN_CLUE),
        flags=np.zeros((1, 1), dtype=int),
        mines_remaining=0,
        status=GameStatus.IN_PROGRESS,
    )

    with pytest.raises(FrozenInstanceError):
        obs.status = GameStatus.WON  # type: ignore[misc]


def test_hidden_clue_cannot_collide_with_real_clue():
    assert HIDDEN_CLUE < 0


@pytest.mark.parametrize("name", types.__all__)
def test_all_names_exist(name: str):
    assert hasattr(types, name)


@pytest.mark.parametrize(
    "name",
    [
        "FlagResult",
        "GameStatus",
        "HIDDEN_CLUE",
        "Observation",
        "RevealResult",
        "Rules",
    ],
)
def test_public_names_are_exported(name: str):
    assert name in types.__all__


def test_result_enums_are_distinct_types():
    assert RevealResult.SUCCESS != FlagResult.SUCCESS
