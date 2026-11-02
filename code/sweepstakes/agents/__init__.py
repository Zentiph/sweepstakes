"""Exports for agents."""

from __future__ import annotations

from typing import Protocol

from ..types import Action, Observation
from .random_agent import RandomAgent

__all__ = ["AGENTS", "Agent"]

AGENTS: dict[str, type[Agent]] = {RandomAgent.name: RandomAgent}


class Agent(Protocol):
    """A Minesweeper agent."""

    name: str

    def act(self, obs: Observation) -> Action: ...
    def reset(self, seed: int) -> None: ...
