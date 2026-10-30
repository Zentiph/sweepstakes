"""
The core shared types for Minesweeper games.
"""

from dataclasses import dataclass
from enum import Enum, auto
import numpy as np

__all__ = [
    "FlagResult",
    "GameStatus",
    "HIDDEN_CLUE",
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

        if (
            self.total_mines < 0
            or self.total_mines
            > self.width * self.height * self.max_mines_per_tile
        ):
            raise ValueError(
                "Total mines must be between 0 and "
                + "width * height * max_mines_per_tile."
            )

        if self.max_mines_per_tile < 1:
            raise ValueError("Max mines per tile must be at least 1.")


class GameStatus(Enum):
    """The status of a Minesweeper game."""

    IN_PROGRESS = auto()
    WON = auto()
    LOST = auto()


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
