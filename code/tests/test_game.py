"""Tests for the core functionality for Minesweeper games."""

import numpy as np
import pytest
from sweepstakes.game import Board, Game, format_grid, get_neighbors
from sweepstakes.types import (
    FlagResult,
    GameStatus,
    HIDDEN_CLUE,
    RevealResult,
    Rules,
)


def find_seed(
    rules: Rules, first_col: int, mine_cols: set[int], radius: int = 0
) -> int:
    """Find a seed that puts mines in the given columns of a one-row board."""
    for seed in range(10_000):
        board = Board(rules, seed, (0, first_col), radius)
        if set(np.flatnonzero(board.counts[0])) == mine_cols:
            return seed
    raise AssertionError("No seed gives the requested layout")


def corridor(first_col: int = 3, mine_col: int = 4) -> tuple[Game, Rules]:
    """Make a 9x1 game with one known mine, with the first cell revealed."""
    rules = Rules(width=9, height=1, total_mines=1, max_mines_per_tile=3)
    game = Game(rules, find_seed(rules, first_col, {mine_col}), 0)
    game.reveal(0, first_col)
    return game, rules


def visible(game: Game) -> list[int]:
    """Get the visible clues of a one-row game."""
    return game.observe().clues[0].tolist()


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


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (
            (1, 1),
            [
                (0, 0),
                (0, 1),
                (0, 2),
                (1, 0),
                (1, 2),
                (2, 0),
                (2, 1),
                (2, 2),
            ],
        ),
        ((0, 0), [(0, 1), (1, 0), (1, 1)]),
        ((2, 2), [(1, 1), (1, 2), (2, 1)]),
        ((0, 1), [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2)]),
    ],
)
def test_get_neighbors(
    location: tuple[int, int], expected: list[tuple[int, int]]
):
    assert list(get_neighbors(location, np.zeros((3, 3)))) == expected


def test_get_neighbors_of_single_cell_board_is_empty():
    assert list(get_neighbors((0, 0), np.zeros((1, 1)))) == []


def test_format_grid():
    assert format_grid([["1", "."], ["#", "F1"]]) == (
        "  |  0  1\n"  #
        "---------\n"
        "0 |  1  .\n"
        "1 |  # F1"
    )


def test_format_grid_pads_row_labels_to_widest():
    lines = format_grid([["."]] * 11).splitlines()

    assert lines[0] == "   |  0"
    assert lines[2] == " 0 |  ."
    assert lines[12] == "10 |  ."


@pytest.mark.parametrize("seed", range(10))
def test_board_clues_count_neighboring_mines(seed: int):
    rules = Rules(width=8, height=6, total_mines=20, max_mines_per_tile=3)
    board = Board(rules, seed, (2, 3))

    for row in range(rules.height):
        for col in range(rules.width):
            neighbors = get_neighbors((row, col), board.counts)
            assert board.clues[row, col] == sum(
                board.counts[neighbor] for neighbor in neighbors
            )


def test_board_clues_count_stacked_mines_not_tiles():
    rules = Rules(width=3, height=3, total_mines=16, max_mines_per_tile=2)
    board = Board(rules, 0, (1, 1), safe_zone_radius=0)

    assert board.clues[1, 1] == 16


def test_board_fills_every_slot_at_full_capacity():
    rules = Rules(width=5, height=5, total_mines=32, max_mines_per_tile=2)
    board = Board(rules, 0, (2, 2))

    expected = np.full((5, 5), 2)
    expected[1:4, 1:4] = 0
    assert np.array_equal(board.counts, expected)


def test_board_different_seeds_give_different_boards(
    rules: Rules, safe_cell: tuple[int, int]
):
    board1 = Board(rules, 1, safe_cell)
    board2 = Board(rules, 2, safe_cell)

    assert not np.array_equal(board1.counts, board2.counts)


def test_board_safe_zone_clips_at_corner():
    rules = Rules(width=3, height=3, total_mines=5, max_mines_per_tile=1)
    board = Board(rules, 0, (0, 0))

    assert board.counts[0:2, 0:2].sum() == 0
    assert board.counts.sum() == 5


def test_board_zero_mines():
    rules = Rules(width=4, height=3, total_mines=0, max_mines_per_tile=1)
    board = Board(rules, 0, (0, 0))

    assert board.counts.sum() == 0
    assert board.clues.sum() == 0
    assert board.safe_cells == 12


def test_board_safe_cells_counts_tiles_not_mines():
    rules = Rules(width=3, height=3, total_mines=16, max_mines_per_tile=2)
    board = Board(rules, 0, (1, 1), safe_zone_radius=0)

    assert board.safe_cells == 1


def test_board_properties_echo_constructor_args(rules: Rules, seed: int):
    board = Board(rules, seed, (2, 3), safe_zone_radius=2)

    assert board.rules == rules
    assert board.seed == seed
    assert board.safe_cell == (2, 3)
    assert board.safe_zone_radius == 2


@pytest.mark.parametrize(
    "safe_cell", [(-1, 0), (0, -1), (10, 0), (0, 10), (10, 10)]
)
def test_board_rejects_off_board_safe_cell(
    rules: Rules, seed: int, safe_cell: tuple[int, int]
):
    with pytest.raises(ValueError, match="Safe cell"):
        Board(rules, seed, safe_cell)


def test_board_rejects_negative_safe_zone_radius(rules: Rules, seed: int):
    with pytest.raises(ValueError, match="radius"):
        Board(rules, seed, (4, 4), safe_zone_radius=-1)


def test_board_rejects_mines_that_do_not_fit_outside_safe_zone():
    rules = Rules(width=3, height=3, total_mines=1, max_mines_per_tile=1)

    with pytest.raises(ValueError, match="Not enough room"):
        Board(rules, 0, (1, 1))


def test_board_str():
    rules = Rules(width=3, height=3, total_mines=8, max_mines_per_tile=1)
    lines = str(Board(rules, 0, (1, 1), safe_zone_radius=0)).splitlines()

    assert lines[2:] == [
        "0 | *1 *1 *1",
        "1 | *1  8 *1",
        "2 | *1 *1 *1",
    ]


def test_board_str_shows_zero_clues_as_dots():
    rules = Rules(width=3, height=1, total_mines=0, max_mines_per_tile=1)

    assert str(Board(rules, 0, (0, 0))).splitlines()[2] == "0 |  .  .  ."


def test_game_starts_unrevealed(rules: Rules, seed: int):
    game = Game(rules, seed)
    obs = game.observe()

    assert game.status == GameStatus.IN_PROGRESS
    assert not game.game_over
    assert game.initial_guess is None
    assert np.all(obs.clues == HIDDEN_CLUE)
    assert np.all(obs.flags == 0)
    assert obs.rules == rules
    assert obs.mines_remaining == rules.total_mines
    assert obs.status == GameStatus.IN_PROGRESS


def test_game_properties_echo_constructor_args(rules: Rules, seed: int):
    game = Game(rules, seed, safe_zone_radius=2)

    assert game.rules == rules
    assert game.seed == seed
    assert game.safe_zone_radius == 2


def test_game_first_reveal_builds_board_around_it(rules: Rules, seed: int):
    game = Game(rules, seed)

    assert game.reveal(2, 7) == RevealResult.SUCCESS
    assert game.initial_guess == (2, 7)
    assert game.observe().clues[2, 7] == 0


def test_game_same_seed_and_moves_give_same_observation(
    rules: Rules, seed: int
):
    game1 = Game(rules, seed)
    game2 = Game(rules, seed)
    game1.reveal(4, 4)
    game2.reveal(4, 4)

    assert np.array_equal(game1.observe().clues, game2.observe().clues)


def test_game_reveal_shows_clues_from_board(rules: Rules, seed: int):
    game = Game(rules, seed)
    game.reveal(4, 4)
    board = Board(rules, seed, (4, 4))

    clues = game.observe().clues
    shown = clues != HIDDEN_CLUE
    assert shown.sum() > 1
    assert np.array_equal(clues[shown], board.clues[shown])
    assert np.all(board.counts[shown] == 0)


def test_game_flood_fill_opens_whole_zero_region(rules: Rules, seed: int):
    game = Game(rules, seed)
    game.reveal(4, 4)
    board = Board(rules, seed, (4, 4))

    clues = game.observe().clues
    for row, col in zip(*np.nonzero(clues == 0)):
        for neighbor in get_neighbors((row, col), board.counts):
            assert clues[neighbor] != HIDDEN_CLUE


def test_game_reveal_of_nonzero_clue_does_not_flood():
    game, _ = corridor()

    assert visible(game) == [-1, -1, -1, 1, -1, -1, -1, -1, -1]


def test_game_flood_fill_stops_at_clues():
    game, _ = corridor()

    assert game.reveal(0, 1) == RevealResult.SUCCESS
    assert visible(game) == [0, 0, 0, 1, -1, -1, -1, -1, -1]


def test_game_flood_fill_skips_flags():
    game, _ = corridor()
    game.flag(0, 0)
    game.reveal(0, 1)

    assert visible(game) == [-1, 0, 0, 1, -1, -1, -1, -1, -1]


def test_game_reveal_mine_loses():
    game, _ = corridor()

    assert game.reveal(0, 4) == RevealResult.LOST
    assert game.status == GameStatus.LOST
    assert game.game_over
    assert game.observe().status == GameStatus.LOST
    # the mine stays hidden from the player's observation
    assert visible(game)[4] == HIDDEN_CLUE


def test_game_reveal_all_safe_cells_wins():
    game, _ = corridor()
    game.reveal(0, 0)
    assert game.reveal(0, 5) == RevealResult.SUCCESS

    assert game.reveal(0, 6) == RevealResult.WON
    assert game.status == GameStatus.WON
    assert game.game_over
    assert game.observe().status == GameStatus.WON


def test_game_first_reveal_can_win():
    rules = Rules(width=5, height=1, total_mines=2, max_mines_per_tile=1)
    game = Game(rules, find_seed(rules, 0, {3, 4}, radius=1))

    assert game.reveal(0, 0) == RevealResult.WON
    assert visible(game) == [0, 0, 1, -1, -1]


def test_game_win_counts_stacked_tiles_once():
    rules = Rules(width=3, height=3, total_mines=16, max_mines_per_tile=2)
    game = Game(rules, 0, safe_zone_radius=0)

    assert game.reveal(1, 1) == RevealResult.WON
    assert game.observe().clues[1, 1] == 16


def test_game_flagged_safe_cell_blocks_win_until_revealed():
    game, _ = corridor()
    game.flag(0, 0)
    game.reveal(0, 1)
    game.reveal(0, 5)

    assert game.reveal(0, 6) == RevealResult.SUCCESS
    assert game.status == GameStatus.IN_PROGRESS

    game.flag(0, 0, flags=0)
    assert game.reveal(0, 0) == RevealResult.WON


@pytest.mark.parametrize(("row", "col"), [(-1, 0), (0, -1), (10, 0), (0, 10)])
def test_game_reveal_off_board(rules: Rules, seed: int, row: int, col: int):
    game = Game(rules, seed)

    assert game.reveal(row, col) == RevealResult.OFF_BOARD
    assert game.initial_guess is None


def test_game_reveal_already_revealed():
    game, _ = corridor()

    assert game.reveal(0, 3) == RevealResult.ALREADY_REVEALED


def test_game_reveal_flagged_cell_is_refused():
    game, _ = corridor()
    game.flag(0, 4)

    assert game.reveal(0, 4) == RevealResult.FLAGGED
    assert game.status == GameStatus.IN_PROGRESS


def test_game_reveal_after_loss():
    game, _ = corridor()
    game.reveal(0, 4)

    assert game.reveal(0, 5) == RevealResult.GAME_OVER
    assert game.reveal(0, 9) == RevealResult.OFF_BOARD


def test_game_reveal_after_win():
    game, _ = corridor()
    game.reveal(0, 0)
    game.reveal(0, 5)
    game.reveal(0, 6)

    assert game.reveal(0, 4) == RevealResult.GAME_OVER
    assert game.status == GameStatus.WON


def test_game_rejects_negative_safe_zone_radius(rules: Rules, seed: int):
    with pytest.raises(ValueError, match="radius"):
        Game(rules, seed, safe_zone_radius=-1)


@pytest.mark.parametrize(
    ("rules", "safe_zone_radius"),
    [
        # room around a corner safe zone, but not a center one
        (Rules(3, 3, 4, 1), 1),
        (Rules(5, 5, 17, 1), 1),
        (Rules(5, 5, 33, 2), 1),
        # the zone clips to the board's single row
        (Rules(4, 1, 2, 1), 1),
        (Rules(3, 3, 1, 1), 5),
    ],
)
def test_game_rejects_mines_that_do_not_fit_around_any_first_reveal(
    rules: Rules, seed: int, safe_zone_radius: int
):
    with pytest.raises(ValueError, match="Not enough room"):
        Game(rules, seed, safe_zone_radius)


@pytest.mark.parametrize(
    ("rules", "safe_zone_radius"),
    [
        (Rules(5, 5, 16, 1), 1),
        (Rules(5, 5, 32, 2), 1),
        (Rules(5, 1, 2, 1), 1),
        (Rules(3, 3, 8, 1), 0),
        (Rules(3, 3, 0, 1), 5),
        (Rules(1, 1, 0, 1), 1),
    ],
)
def test_game_accepted_rules_allow_any_first_reveal(
    rules: Rules, seed: int, safe_zone_radius: int
):
    for row in range(rules.height):
        for col in range(rules.width):
            game = Game(rules, seed, safe_zone_radius)

            assert game.reveal(row, col) in (
                RevealResult.SUCCESS,
                RevealResult.WON,
            )


def test_game_flag_before_board_generated(rules: Rules, seed: int):
    game = Game(rules, seed)

    assert game.flag(0, 0) == FlagResult.BOARD_NOT_GENERATED
    assert game.flag(-1, 0) == FlagResult.BOARD_NOT_GENERATED
    assert game.observe().flags.sum() == 0


def test_game_flag_cycles_through_counts_and_back_to_zero():
    game, _ = corridor()

    seen = []
    for _ in range(4):
        assert game.flag(0, 0) == FlagResult.SUCCESS
        seen.append(int(game.observe().flags[0, 0]))

    assert seen == [1, 2, 3, 0]


@pytest.mark.parametrize("flags", [0, 1, 3])
def test_game_flag_sets_explicit_count(flags: int):
    game, _ = corridor()
    game.flag(0, 0, flags=2)

    assert game.flag(0, 0, flags=flags) == FlagResult.SUCCESS
    assert game.observe().flags[0, 0] == flags


@pytest.mark.parametrize("flags", [-1, 4])
def test_game_flag_rejects_invalid_count(flags: int):
    game, _ = corridor()
    game.flag(0, 0, flags=2)

    assert game.flag(0, 0, flags=flags) == FlagResult.INVALID_FLAG_COUNT
    assert game.observe().flags[0, 0] == 2


@pytest.mark.parametrize(("row", "col"), [(-1, 0), (0, -1), (1, 0), (0, 9)])
def test_game_flag_off_board(row: int, col: int):
    game, _ = corridor()

    assert game.flag(row, col) == FlagResult.OFF_BOARD


def test_game_flag_already_revealed():
    game, _ = corridor()

    assert game.flag(0, 3) == FlagResult.ALREADY_REVEALED
    assert game.observe().flags[0, 3] == 0


def test_game_flag_after_game_over():
    game, _ = corridor()
    game.reveal(0, 4)

    assert game.flag(0, 0) == FlagResult.GAME_OVER
    assert game.flag(0, 9) == FlagResult.OFF_BOARD


def test_game_mines_remaining_tracks_flag_counts():
    game, _ = corridor()
    assert game.mines_remaining == 1

    game.flag(0, 0, flags=1)
    assert game.mines_remaining == 0
    assert game.observe().mines_remaining == 0

    # over-flagging is allowed, so the count can go negative
    game.flag(0, 1, flags=3)
    assert game.mines_remaining == -3


def test_game_observation_is_read_only(rules: Rules, seed: int):
    game = Game(rules, seed)
    game.reveal(4, 4)
    obs = game.observe()

    with pytest.raises(ValueError):
        obs.clues[0, 0] = 5
    with pytest.raises(ValueError):
        obs.flags[0, 0] = 1


def test_game_observation_is_a_snapshot():
    game, _ = corridor()
    obs = game.observe()
    game.flag(0, 0)
    game.reveal(0, 1)

    assert obs.flags[0, 0] == 0
    assert obs.clues[0, 1] == HIDDEN_CLUE
    assert obs.mines_remaining == 1


def test_game_str_before_board_generated():
    rules = Rules(width=2, height=1, total_mines=0, max_mines_per_tile=1)

    assert str(Game(rules, 0)).splitlines()[2] == "0 |  #  #"


def test_game_str_shows_clues_flags_and_hidden_cells():
    game, _ = corridor()
    game.flag(0, 8, flags=2)
    game.reveal(0, 1)

    assert str(game).splitlines()[2].split()[2:] == [
        ".",
        ".",
        ".",
        "1",
        "#",
        "#",
        "#",
        "#",
        "F2",
    ]


def test_game_str_hides_mines_while_in_progress():
    game, _ = corridor()

    assert "*" not in str(game)
    assert "X" not in str(game)


def test_game_str_shows_mines_after_loss():
    rules = Rules(width=4, height=1, total_mines=2, max_mines_per_tile=1)
    game = Game(rules, find_seed(rules, 0, {1, 3}), 0)
    game.reveal(0, 0)
    game.reveal(0, 1)

    assert str(game).splitlines()[2].split()[2:] == ["1", "X", "#", "*1"]
