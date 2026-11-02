"""Test the agents against the game."""

from time import perf_counter

import numpy as np

from .agents import Agent
from .game import Game
from .types import (
    HIDDEN_CLUE,
    ActionKind,
    FlagResult,
    GameRecord,
    GameStatus,
    RevealResult,
)

MAX_FAILS = 20
"""
How many invalid actions an agent is allowed to make before force-ending a game.
"""


def play_game(game: Game, agent: Agent, agent_seed: int) -> GameRecord:
    """Make an agent play a game of minesweeper.

    The first chosen cell is always the middle cell, calculated from
    `game.rules.height // 2` and `game.rules.width // 2`.

    Args:
        game (Game): The game to play.
        agent (Agent): The agent to play with.
        agent_seed (int): The seed to use for the agent.

    Returns:
        GameRecord: The game record.
    """
    assert game.status == GameStatus.NOT_STARTED

    agent.reset(agent_seed)
    game.reveal(game.rules.height // 2, game.rules.width // 2)

    max_alloted_actions = (
        game.rules.height
        * game.rules.width
        * (game.rules.max_mines_per_tile + 2)
    )
    failed_actions = 0

    actions = 0
    reveals = 0
    guesses = 0
    total_time = 0.0

    while not game.game_over:
        obs = game.observe()

        start_time = perf_counter()
        action = agent.act(obs)
        action_time = perf_counter() - start_time

        actions += 1
        if actions >= max_alloted_actions:
            break

        if action.kind == ActionKind.REVEAL:
            reveal_result = game.reveal(action.row, action.col)
            # invalid move
            if reveal_result not in {
                RevealResult.SUCCESS,
                RevealResult.WON,
                RevealResult.LOST,
            }:
                failed_actions += 1
                if failed_actions >= MAX_FAILS:
                    break
            else:  # valid
                # only update metrics data on successful reveals
                # agents shouldn't be making invalid reveals
                # unless they're buggy, and flags are unnecessary to track
                # for performance and are simply present for visualization
                reveals += 1
                guesses += action.is_guess
                total_time += action_time

        else:  # ActionKind.FLAG
            if action.flags is None:
                # disallow agents to cycle flags
                flag_result = FlagResult.INVALID_FLAG_COUNT
            else:
                flag_result = game.flag(
                    action.row, action.col, flags=action.flags
                )

            if flag_result != FlagResult.SUCCESS:
                failed_actions += 1
                if failed_actions >= MAX_FAILS:
                    break

    # if the game was cancelled due to alternate failure
    # (too many reveals, too many mistakes, etc.)
    if not game.game_over:
        game.abort()

    return GameRecord(
        status=game.status,
        safe_cells_revealed=int(
            np.count_nonzero(game.observe().clues != HIDDEN_CLUE)
        ),
        # should never return None, but -1 as fallback to be safe
        total_safe_cells=game.safe_cells if game.safe_cells is not None else -1,
        reveals=reveals,
        guesses=guesses,
        time_seconds=total_time,
        seed=game.seed,
        agent_name=agent.name,
        agent_seed=agent_seed,
    )
