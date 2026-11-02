"""Exports for agents."""

from __future__ import annotations

from typing import Protocol

from ..types import Action, Observation
from .random_agent import RandomAgent

__all__ = ["AGENTS", "Agent"]

AGENTS: dict[str, type[Agent]] = {RandomAgent.name: RandomAgent}
"""
Every agent available to the CLI and experiments, by name. Register a new
agent by adding its class here.
"""


class Agent(Protocol):
    """A Minesweeper agent.

    Agents are constructed with no arguments.
    """

    name: str
    """The agent's unique name in the registry."""

    def act(self, obs: Observation) -> Action:
        """Choose the next action.

        Args:
            obs (Observation): The current view of the game.

        Returns:
            Action: The action to take.
        """
        ...

    def reset(self, seed: int) -> None:
        """Prepare for a new game. Called before the first `act`.

        Args:
            seed (int): The non-negative seed for the agent's random choices.
        """
        ...
