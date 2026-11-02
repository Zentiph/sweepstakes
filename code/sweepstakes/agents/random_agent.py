"""A baseline random agent."""

import numpy as np

from ..types import HIDDEN_CLUE, Action, ActionKind, Observation

__all__ = ["RandomAgent"]


class RandomAgent:
    """Reveals a uniformly random hidden, unflagged cell every turn.

    Serves as the performance floor for other agents.
    """

    name = "random"

    def __init__(self) -> None:
        self.__rng: np.random.Generator | None = None

    def act(self, obs: Observation) -> Action:
        """Choose a random hidden, unflagged cell to reveal.

        Args:
            obs (Observation): The current view of the game.

        Returns:
            Action: A reveal action, always marked as a guess.
        """
        if self.__rng is None:
            raise RuntimeError(
                "Agent must be reset with reset() before calling act()"
            )

        # True where cells are hidden and have no flags
        candidates_mark = (obs.clues == HIDDEN_CLUE) & (obs.flags == 0)

        # (row, col) coordinates of every True cell, one pair per row
        candidates = np.argwhere(candidates_mark)
        if len(candidates) == 0:
            raise RuntimeError("No hidden, unflagged cells to reveal")

        row, col = candidates[self.__rng.integers(len(candidates))]

        return Action(
            kind=ActionKind.REVEAL, row=int(row), col=int(col), is_guess=True
        )

    def reset(self, seed: int) -> None:
        """Prepare for a new game.

        Args:
            seed (int): The seed for this agent's random choices.
        """
        self.__rng = np.random.default_rng(seed)
