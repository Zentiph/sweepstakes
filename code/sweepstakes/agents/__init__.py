"""Exports for agents."""

from typing import Protocol

from ..types import Action, Observation


class Agent(Protocol):
    """A Minesweeper agent."""

    name: str

    def act(self, obs: Observation) -> Action: ...
    def reset(self, seed: int) -> None: ...
