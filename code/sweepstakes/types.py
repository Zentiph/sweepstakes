"""
The core types for Minesweeper games.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    """The rules of a Minesweeper game."""

    width: int
    height: int
    total_mines: int
    max_mines_per_tile: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("Dimensions must be at least 1.")

        if self.total_mines < 0 or self.total_mines > self.width * self.height:
            raise ValueError("Total mines must be between 0 and width * height.")

        if self.max_mines_per_tile < 1:
            raise ValueError("Max stack must be at least 1.")
