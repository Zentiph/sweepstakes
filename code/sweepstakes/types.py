"""
The core types for Minesweeper games.
"""

from dataclasses import dataclass

import numpy as np

__all__ = [
    "Board",
    "Rules",
]


def format_grid(cells: list[list[str]]) -> str:
    """Lay out a grid of cell strings with row and column numbers.

    Args:
        cells (list[list[str]]): The grid of cells.

    Returns:
        str: The formatted grid.
    """
    height = len(cells)
    width = len(cells[0])
    label_width = len(str(height - 1))  # widest row number

    header = (
        " " * label_width
        + " | "
        + " ".join(f"{col:>2}" for col in range(width))
    )
    lines = [header, "-" * len(header)]
    for row_i, row in enumerate(cells):
        lines.append(
            f"{row_i:>{label_width}} | "
            + " ".join(f"{cell:>2}" for cell in row)
        )
    return "\n".join(lines)


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


class Board:
    """The true state of a Minesweeper game."""

    def __init__(
        self,
        rules: Rules,
        seed: int,
        safe_cell: tuple[int, int],
        safe_zone_radius: int = 1,
    ) -> None:
        """Generate a new Minesweeper board.

        Args:
            rules (Rules): The rules of the game.
            seed (int): The seed for the random number generator.
            safe_cell (tuple[int, int]): The initial safe cell (y, x).
            safe_zone_radius (int, optional): The radius of the initial safe zone. Defaults to 1.
        """
        if (
            safe_cell[0] < 0
            or safe_cell[1] < 0
            or safe_cell[0] >= rules.height
            or safe_cell[1] >= rules.width
        ):
            raise ValueError(
                "Safe cell must be on the board "
                + f"(y by x bounds: {rules.height} by {rules.width}, "
                + f"got: {safe_cell})"
            )
        if safe_zone_radius < 0:
            raise ValueError("Safe zone radius must be non-negative")

        self.rules = rules
        self.seed = seed
        self.safe_cell = safe_cell

        width = rules.width
        height = rules.height
        max_mine_stack = rules.max_mines_per_tile
        total_mines = rules.total_mines

        rng = np.random.default_rng(seed)

        # build the board with all cells as eligible
        eligible = np.ones((height, width), dtype=bool)
        # exclude the safe zone
        r0 = max(safe_cell[0] - safe_zone_radius, 0)
        r1 = min(safe_cell[0] + safe_zone_radius + 1, height)
        c0 = max(safe_cell[1] - safe_zone_radius, 0)
        c1 = min(safe_cell[1] + safe_zone_radius + 1, width)
        eligible[r0:r1, c0:c1] = False

        # get the eligible mine locations (nonzero cells)
        eligible_cells = np.flatnonzero(eligible)

        # since mine stacking allows for multiple mines in one cell,
        # giving each cell the max stack amount number of slots allows
        # for the same cell to be sampled multiple times, allowing for true
        # random generation of mine-stacked boards
        n_slots = eligible_cells.size * max_mine_stack
        if total_mines > n_slots:
            raise ValueError(
                "Not enough room for the mines outside the safe zone"
            )

        chosen_slots = rng.choice(n_slots, size=total_mines, replace=False)

        # in a case with max_mines_per_tile = 2 and eligible cells [0, 1, 3]:
        # slot: 0 1 | 2 3 | 4 5
        # cell: 0 0 | 1 1 | 3 3
        # so slot s belongs to eligible_cells[s // 2]
        mined_cells = eligible_cells[chosen_slots // max_mine_stack]

        # bincount counts how often each flat index (mine location) appears
        self.counts = np.bincount(
            mined_cells, minlength=height * width
        ).reshape(height, width)

        # pad the board with zeros for use in calculating clue counts
        padded = np.pad(self.counts, 1)
        clues = np.zeros((height, width), dtype=int)
        for row_offset in (-1, 0, 1):
            for col_offset in (-1, 0, 1):
                if row_offset == 0 and col_offset == 0:
                    continue  # skip the cell itself

                # 1 more than the original offsets because
                # the padding shifted the board
                first_row = row_offset + 1
                first_col = col_offset + 1

                neighbor_counts = padded[
                    first_row : first_row + height,
                    first_col : first_col + width,
                ]

                # add up the mines from each direction
                # to get the total clue value
                clues += neighbor_counts

        self.clues = clues

    def __str__(self) -> str:
        cells = [
            [
                Board._tile_to_string(clue, mine_count)
                for clue, mine_count in zip(clue_row, count_row)
            ]
            for clue_row, count_row in zip(self.clues, self.counts)
        ]
        return format_grid(cells)

    @staticmethod
    def _tile_to_string(clue: int, mine_count: int) -> str:
        if mine_count > 0:
            return f"*{mine_count}"
        if clue == 0:
            return "."
        return str(clue)
