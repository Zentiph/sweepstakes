"""
The core shared types for Minesweeper games.
"""

from dataclasses import dataclass

__all__ = [
    "Rules",
]


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
