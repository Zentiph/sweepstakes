"""Tests for the agents."""

import numpy as np
import pytest

from sweepstakes.agents import AGENTS
from sweepstakes.agents.random_agent import RandomAgent
from sweepstakes.game import Game
from sweepstakes.types import (
    HIDDEN_CLUE,
    ActionKind,
    GameStatus,
    Observation,
    Rules,
)

RULES = Rules(width=9, height=9, total_mines=10, max_mines_per_tile=1)


@pytest.fixture
def game() -> Game:
    game = Game(RULES, 4)
    game.reveal(4, 4)
    return game


@pytest.mark.parametrize("name", sorted(AGENTS))
def test_registry_agents_construct_without_arguments(name: str):
    agent = AGENTS[name]()

    assert agent.name == name


def test_random_agent_must_be_reset_first(game: Game):
    with pytest.raises(RuntimeError, match="reset"):
        RandomAgent().act(game.observe())


def test_random_agent_reveals_hidden_unflagged_guesses(game: Game):
    game.flag(0, 5)
    obs = game.observe()
    agent = RandomAgent()
    agent.reset(0)

    for _ in range(100):
        action = agent.act(obs)
        assert action.kind == ActionKind.REVEAL
        assert action.is_guess
        assert obs.clues[action.row, action.col] == HIDDEN_CLUE
        assert obs.flags[action.row, action.col] == 0


def test_random_agent_is_deterministic_per_seed(game: Game):
    obs = game.observe()

    def actions(seed: int) -> list[tuple[int, int]]:
        agent = RandomAgent()
        agent.reset(seed)
        return [(a.row, a.col) for a in (agent.act(obs) for _ in range(20))]

    assert actions(1) == actions(1)
    assert actions(1) != actions(2)


def test_random_agent_reset_restarts_choices(game: Game):
    obs = game.observe()
    agent = RandomAgent()

    agent.reset(3)
    first = [agent.act(obs) for _ in range(10)]
    agent.reset(3)

    assert [agent.act(obs) for _ in range(10)] == first


def test_random_agent_fails_with_no_hidden_unflagged_cells():
    obs = Observation(
        rules=RULES,
        clues=np.full((9, 9), HIDDEN_CLUE),
        flags=np.ones((9, 9), dtype=int),
        mines_remaining=RULES.total_mines - 81,
        status=GameStatus.IN_PROGRESS,
    )
    agent = RandomAgent()
    agent.reset(0)

    with pytest.raises(RuntimeError, match="No hidden"):
        agent.act(obs)
