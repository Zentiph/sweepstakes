"""Tests for the core types for Minesweeper games."""

import numpy as np
import pytest
from sweepstakes.types import Board, Rules


@pytest.fixture
def rules() -> Rules:
    return Rules(width=10, height=10, total_mines=16, max_mines_per_tile=2)


@pytest.fixture
def seed() -> int:
    return 301655


@pytest.fixture
def safe_cell() -> tuple[int, int]:
    return (4, 4)


@pytest.fixture
def safe_zone_radius() -> int:
    return 1


def test_board_same_params_gives_same_board(
    rules: Rules, seed: int, safe_cell: tuple[int, int], safe_zone_radius: int
):
    board1 = Board(
        rules=rules,
        seed=seed,
        safe_cell=safe_cell,
        safe_zone_radius=safe_zone_radius,
    )
    board2 = Board(
        rules=rules,
        seed=seed,
        safe_cell=safe_cell,
        safe_zone_radius=safe_zone_radius,
    )

    assert np.array_equal(board1.clues, board2.clues)
    assert np.array_equal(board1.counts, board2.counts)


def test_board_arrays_match_rules(
    rules: Rules, seed: int, safe_cell: tuple[int, int], safe_zone_radius: int
):
    board = Board(
        rules=rules,
        seed=seed,
        safe_cell=safe_cell,
        safe_zone_radius=safe_zone_radius,
    )

    assert board.counts.sum() == rules.total_mines
    assert board.counts.max() <= rules.max_mines_per_tile


def test_board_safe_zone_has_no_mines(
    rules: Rules, seed: int, safe_cell: tuple[int, int], safe_zone_radius: int
):
    board = Board(
        rules=rules,
        seed=seed,
        safe_cell=safe_cell,
        safe_zone_radius=safe_zone_radius,
    )

    r0 = max(safe_cell[0] - safe_zone_radius, 0)
    r1 = min(safe_cell[0] + safe_zone_radius + 1, rules.height)
    c0 = max(safe_cell[1] - safe_zone_radius, 0)
    c1 = min(safe_cell[1] + safe_zone_radius + 1, rules.width)

    assert np.array_equal(
        board.counts[r0:r1, c0:c1], np.zeros((r1 - r0, c1 - c0))
    )
    # only the safe cell's clue is guaranteed to be 0; edge cells of the
    # safe zone can still border mines outside it
    assert board.clues[safe_cell] == 0
