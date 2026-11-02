"""
The core shared types for Minesweeper games.
"""

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

__all__ = [
    "HIDDEN_CLUE",
    "Action",
    "ActionKind",
    "FlagResult",
    "GameRecord",
    "GameStatus",
    "Observation",
    "RevealResult",
    "Rules",
]

HIDDEN_CLUE = -1
"""The value of a clue that is hidden."""


@dataclass(frozen=True, slots=True)
class Rules:
    """The rules of a Minesweeper game."""

    width: int
    height: int
    total_mines: int
    max_mines_per_tile: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("Dimensions must be at least 1.")

        if self.max_mines_per_tile < 1:
            raise ValueError("Max mines per tile must be at least 1.")

        if (
            self.total_mines < 0
            or self.total_mines
            > self.width * self.height * self.max_mines_per_tile
        ):
            raise ValueError(
                "Total mines must be between 0 and "
                + "width * height * max_mines_per_tile."
            )


class GameStatus(Enum):
    """The status of a Minesweeper game."""

    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    WON = auto()
    LOST = auto()
    ABORTED = auto()


@dataclass(frozen=True, slots=True)
class GameRecord:
    """A record of a Minesweeper game."""

    status: GameStatus
    safe_cells_revealed: int
    total_safe_cells: int
    reveals: int
    guesses: int
    time_seconds: float
    seed: int
    agent_name: str
    agent_seed: int


class RevealResult(Enum):
    """The result of revealing a cell."""

    # valid action results
    SUCCESS = auto()
    WON = auto()
    LOST = auto()

    # invalid action results
    OFF_BOARD = auto()
    ALREADY_REVEALED = auto()
    FLAGGED = auto()
    GAME_OVER = auto()


class FlagResult(Enum):
    """The result of flagging a cell."""

    # valid action results
    SUCCESS = auto()

    # invalid action results
    INVALID_FLAG_COUNT = auto()
    BOARD_NOT_GENERATED = auto()
    OFF_BOARD = auto()
    ALREADY_REVEALED = auto()
    GAME_OVER = auto()


@dataclass(frozen=True, slots=True)
class Observation:
    """Everything a player is allowed to know about a game."""

    rules: Rules
    clues: np.ndarray
    flags: np.ndarray
    mines_remaining: int
    status: GameStatus


class ActionKind(Enum):
    """A kind of action that can be taken in a game."""

    REVEAL = auto()
    FLAG = auto()


@dataclass(frozen=True, slots=True)
class Action:
    """An action that can be taken in a game."""

    kind: ActionKind
    row: int
    col: int
    flags: int | None = None
    """The number of flags placed if kind is FLAG. Otherwise None."""
    is_guess: bool = False
    """Whether the action is a guess (could not be determined through logic)."""
