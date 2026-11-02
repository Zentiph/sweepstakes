"""Tests for running agents against games."""

from collections.abc import Callable

import numpy as np
import pytest

from sweepstakes.experiments import MAX_FAILS, apply_action, play_game
from sweepstakes.game import Board, Game
from sweepstakes.types import (
    HIDDEN_CLUE,
    Action,
    ActionKind,
    GameStatus,
    Observation,
    Rules,
)

RULES = Rules(width=9, height=9, total_mines=10, max_mines_per_tile=1)
SEED = 4
CENTER = (4, 4)


class ScriptedAgent:
    """An agent that asks a function for each action."""

    name = "scripted"

    def __init__(self, choose: Callable[[Observation], Action]) -> None:
        self.choose = choose
        self.reset_seed: int | None = None
        self.calls = 0

    def reset(self, seed: int) -> None:
        self.reset_seed = seed

    def act(self, obs: Observation) -> Action:
        self.calls += 1
        return self.choose(obs)


@pytest.fixture
def board() -> Board:
    # the board play_game builds, since it always opens on the center
    return Board(RULES, SEED, CENTER)


def hidden(
    obs: Observation, mines: bool, board: Board
) -> list[tuple[int, int]]:
    """Get the hidden cells that are (or aren't) mines."""
    cells = np.argwhere(
        (obs.clues == HIDDEN_CLUE) & ((board.counts > 0) == mines)
    )
    return [(int(row), int(col)) for row, col in cells]


def test_apply_action_reveal(board: Board):
    game = Game(RULES, SEED)
    game.reveal(*CENTER)
    safe = hidden(game.observe(), False, board)[0]

    assert apply_action(game, Action(ActionKind.REVEAL, *safe))
    assert not apply_action(game, Action(ActionKind.REVEAL, *safe))
    assert not apply_action(game, Action(ActionKind.REVEAL, -1, 0))


@pytest.mark.parametrize(
    ("flags", "valid"), [(None, False), (0, True), (1, True), (2, False)]
)
def test_apply_action_flag(board: Board, flags: int | None, valid: bool):
    game = Game(RULES, SEED)
    game.reveal(*CENTER)
    cell = hidden(game.observe(), True, board)[0]

    assert apply_action(game, Action(ActionKind.FLAG, *cell, flags)) == valid
    # cycling is refused without touching the flags
    expected = flags if valid else 0
    assert game.observe().flags[cell] == expected


def test_apply_action_reveal_mine_is_valid(board: Board):
    game = Game(RULES, SEED)
    game.reveal(*CENTER)
    mine = hidden(game.observe(), True, board)[0]

    assert apply_action(game, Action(ActionKind.REVEAL, *mine))
    assert game.status == GameStatus.LOST


def test_play_game_reveals_safe_cells_to_win(board: Board):
    def choose(obs: Observation) -> Action:
        row, col = hidden(obs, False, board)[0]
        # mark every other reveal as a guess
        return Action(
            ActionKind.REVEAL, row, col, is_guess=agent.calls % 2 == 0
        )

    agent = ScriptedAgent(choose)
    record = play_game(Game(RULES, SEED), agent, 7)

    assert record.status == GameStatus.WON
    assert record.reveals == agent.calls
    assert record.guesses == agent.calls // 2
    assert record.safe_cells_revealed == board.safe_cells
    assert record.total_safe_cells == board.safe_cells
    assert record.time_seconds >= 0


def test_play_game_records_its_inputs():
    agent = ScriptedAgent(lambda obs: Action(ActionKind.REVEAL, -1, -1))
    record = play_game(Game(RULES, SEED), agent, 7)

    assert agent.reset_seed == 7
    assert record.seed == SEED
    assert record.agent_name == "scripted"
    assert record.agent_seed == 7


def test_play_game_counts_losing_reveal(board: Board):
    agent = ScriptedAgent(
        lambda obs: Action(ActionKind.REVEAL, *hidden(obs, True, board)[0])
    )
    record = play_game(Game(RULES, SEED), agent, 0)

    assert record.status == GameStatus.LOST
    assert record.reveals == 1
    assert record.guesses == 0


def test_play_game_does_not_count_flags_as_reveals(board: Board):
    def choose(obs: Observation) -> Action:
        unflagged_mines = [
            cell for cell in hidden(obs, True, board) if obs.flags[cell] == 0
        ]
        if unflagged_mines:
            return Action(ActionKind.FLAG, *unflagged_mines[0], flags=1)
        return Action(ActionKind.REVEAL, *hidden(obs, False, board)[0])

    agent = ScriptedAgent(choose)
    record = play_game(Game(RULES, SEED), agent, 0)

    assert record.status == GameStatus.WON
    assert record.reveals == agent.calls - RULES.total_mines


@pytest.mark.parametrize(
    "action",
    [
        Action(ActionKind.REVEAL, -1, -1),
        Action(ActionKind.REVEAL, *CENTER),
        # agents can't cycle flags
        Action(ActionKind.FLAG, 0, 5, flags=None),
    ],
)
def test_play_game_aborts_after_max_fails(action: Action):
    agent = ScriptedAgent(lambda obs: action)
    record = play_game(Game(RULES, SEED), agent, 0)

    assert record.status == GameStatus.ABORTED
    assert agent.calls == MAX_FAILS
    assert record.reveals == 0


def test_play_game_aborts_when_out_of_actions(board: Board):
    # toggling a flag is always valid, so only the budget can stop it
    def choose(obs: Observation) -> Action:
        cell = hidden(obs, True, board)[0]
        return Action(ActionKind.FLAG, *cell, flags=1 - int(obs.flags[cell]))

    agent = ScriptedAgent(choose)
    record = play_game(Game(RULES, SEED), agent, 0)

    assert record.status == GameStatus.ABORTED
    assert agent.calls == RULES.height * RULES.width * (
        RULES.max_mines_per_tile + 2
    )


def test_play_game_hook_sees_each_step_after_it_is_applied(board: Board):
    steps: list[tuple[Action | None, bool]] = []

    def on_step(game: Game, action: Action | None) -> None:
        cell = CENTER if action is None else (action.row, action.col)
        revealed = game.observe().clues[cell] != HIDDEN_CLUE
        steps.append((action, bool(revealed)))

    agent = ScriptedAgent(
        lambda obs: Action(ActionKind.REVEAL, *hidden(obs, False, board)[0])
    )
    record = play_game(Game(RULES, SEED), agent, 0, on_step=on_step)

    assert steps[0] == (None, True)
    assert len(steps) == agent.calls + 1
    assert all(revealed for _, revealed in steps)
    assert record.status == GameStatus.WON


def test_play_game_hook_can_abort(board: Board):
    def on_step(game: Game, action: Action | None) -> None:
        if action is not None:
            game.abort()

    agent = ScriptedAgent(
        lambda obs: Action(ActionKind.REVEAL, *hidden(obs, False, board)[0])
    )
    record = play_game(Game(RULES, SEED), agent, 0, on_step=on_step)

    assert record.status == GameStatus.ABORTED
    assert agent.calls == 1
    assert record.reveals == 1


def test_play_game_requires_a_new_game():
    game = Game(RULES, SEED)
    game.reveal(*CENTER)

    with pytest.raises(AssertionError):
        play_game(
            game, ScriptedAgent(lambda obs: Action(ActionKind.REVEAL, 0, 0)), 0
        )
