"""Core functionality for the minesweeper game engine."""

import numpy as np

from .types import (
    Rules,
    GameStatus,
    RevealResult,
    FlagResult,
    Observation,
    HIDDEN_CLUE,
)
from typing import Generator
from collections import deque

__all__ = ["Board", "Game"]


def get_neighbors(
    location: tuple[int, int], board: np.ndarray
) -> Generator[tuple[int, int], None, None]:
    """Get the neighbors of a location in a 2D board.

    Neighbors are evaluated left-to-right, top-to-bottom.

    Args:
        location (tuple[int, int]): The location to get the neighbors of.
        board (np.ndarray): The board to get the neighbors from.

    Yields:
        tuple[int, int]: Each neighbor.
    """
    for row_offset in (-1, 0, 1):
        for col_offset in (-1, 0, 1):
            if row_offset == 0 and col_offset == 0:
                continue  # don't count the location itself

            neighbor_row = location[0] + row_offset
            neighbor_col = location[1] + col_offset

            # bounds check
            if neighbor_row < 0 or neighbor_row >= board.shape[0]:
                continue
            if neighbor_col < 0 or neighbor_col >= board.shape[1]:
                continue

            yield (neighbor_row, neighbor_col)


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


class Board:
    """The true state of a Minesweeper game."""

    __slots__ = [
        "__clues",
        "__counts",
        "__rules",
        "__safe_cell",
        "__safe_zone_radius",
        "__seed",
    ]

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

        self.__rules = rules
        self.__seed = seed
        self.__safe_cell = safe_cell
        self.__safe_zone_radius = safe_zone_radius

        width = self.__rules.width
        height = self.__rules.height
        max_mine_stack = self.__rules.max_mines_per_tile
        total_mines = self.__rules.total_mines

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
        self.__counts = np.bincount(
            mined_cells, minlength=height * width
        ).reshape(height, width)

        # pad the board with zeros for use in calculating clue counts
        padded = np.pad(self.__counts, 1)
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

        self.__clues = clues

    @property
    def counts(self) -> np.ndarray:
        """Get the count of mines in each cell.

        Returns:
            np.ndarray: The count of mines in each cell.
        """
        return self.__counts

    @property
    def clues(self) -> np.ndarray:
        """Get the clue value in each cell.

        Returns:
            np.ndarray: The clue value in each cell.
        """
        return self.__clues

    @property
    def safe_cells(self) -> int:
        """Get the number of safe cells in the board.

        Returns:
            int: The number of safe cells.
        """
        return int((self.counts == 0).sum())

    @property
    def rules(self) -> Rules:
        """Get the rules used to generate the board.

        Returns:
            Rules: The rules used to generate the board.
        """
        return self.__rules

    @property
    def seed(self) -> int:
        """Get the seed used to generate the board.

        Returns:
            int: The seed used to generate the board.
        """
        return self.__seed

    @property
    def safe_cell(self) -> tuple[int, int]:
        """Get the initial safe cell.

        Returns:
            tuple[int, int]: The initial safe cell.
        """
        return self.__safe_cell

    @property
    def safe_zone_radius(self) -> int:
        """Get the initial safe zone radius.

        Returns:
            int: The initial safe zone radius.
        """
        return self.__safe_zone_radius

    def __str__(self) -> str:
        cells = [
            [
                Board.__tile_to_str(clue=clue, mine_count=mine_count)
                for clue, mine_count in zip(clue_row, count_row)
            ]
            for clue_row, count_row in zip(self.clues, self.counts)
        ]
        return format_grid(cells)

    @staticmethod
    def __tile_to_str(*, clue: int, mine_count: int) -> str:
        if mine_count > 0:
            return f"*{mine_count}"
        if clue == 0:
            return "."
        return str(clue)


class Game:
    """Represents a game of minesweeper."""

    __slots__ = (
        "__board",
        "__exploded_cell",
        "__flags",
        "__revealed",
        "__rules",
        "__safe_cells",
        "__safe_zone_radius",
        "__seed",
        "__status",
    )

    def __init__(
        self, rules: Rules, seed: int, safe_zone_radius: int = 1
    ) -> None:
        """Setup a new minesweeper game.

        The board is generated after the first move, on the premise that the
        first chosen cell is always safe.

        Args:
            rules (Rules): The rules for the game.
            seed (int): The seed to generate the board with.
            safe_zone_radius (int, optional): The radius of the safe zone. Defaults to 1.
        """
        if safe_zone_radius < 0:
            raise ValueError("Safe zone radius must be non-negative")

        # the first reveal can be anywhere, so the mines must fit
        # around the largest safe zone (one that isn't clipped by an edge)
        zone_size = 2 * safe_zone_radius + 1
        largest_zone = min(zone_size, rules.height) * min(
            zone_size, rules.width
        )
        n_slots = (
            rules.height * rules.width - largest_zone
        ) * rules.max_mines_per_tile
        if rules.total_mines > n_slots:
            raise ValueError(
                "Not enough room for the mines outside the safe zone"
            )

        self.__rules = rules
        self.__seed = seed
        self.__safe_zone_radius = safe_zone_radius

        # game state:
        self.__revealed = np.zeros((rules.height, rules.width), dtype=bool)
        # because stacked mines are allowed, you can flag up to
        # rules.max_mines_per_tile times on one tile
        self.__flags = np.zeros((rules.height, rules.width), dtype=int)

        # will be initialized on first reveal
        self.__board: Board | None = None
        self.__safe_cells = 0
        self.__exploded_cell: tuple[int, int] | None = None

        self.__status = GameStatus.IN_PROGRESS

    def reveal(self, row: int, col: int) -> RevealResult:
        """Reveal a cell on the board.

        If the board has not been generated yet, it will be generated
        with the revealed cell as the safe anchor.

        Revealed cells with a clue value of 0 flood-fill their neighbors,
        skipping flags.

        Args:
            row (int): The row of the cell to reveal.
            col (int): The column of the cell to reveal.

        Returns:
            RevealResult: The result of the reveal.
        """
        if (
            row < 0
            or row >= self.__rules.height
            or col < 0
            or col >= self.__rules.width
        ):
            return RevealResult.OFF_BOARD
        if self.game_over:
            return RevealResult.GAME_OVER
        if self.__revealed[row, col]:
            return RevealResult.ALREADY_REVEALED
        if self.__flags[row, col] > 0:
            return RevealResult.FLAGGED

        board = self.__board

        if board is None:
            # first reveal
            # build the board with the revealed tile as safe anchor
            board = Board(
                self.__rules, self.__seed, (row, col), self.__safe_zone_radius
            )
            self.__board = board
            self.__safe_cells = board.safe_cells

        if board.counts[row, col] > 0:
            self.__exploded_cell = (row, col)
            self.__status = GameStatus.LOST
            return RevealResult.LOST

        self.__revealed[row, col] = True

        if board.clues[row, col] == 0:
            self.__flood_fill(row, col)

        if self.__win_check():
            return RevealResult.WON
        return RevealResult.SUCCESS

    def flag(
        self, row: int, col: int, *, flags: int | None = None
    ) -> FlagResult:
        """Flag a cell on the board.

        If the board has not been generated yet, this operation will fail.

        Args:
            row (int): The row of the cell to flag.
            col (int): The column of the cell to flag.
            flags (int | None, optional): The number of flags to place. Leave as
            None to cycle through flag counts. Defaults to None.

        Returns:
            FlagResult: The result of the flag.
        """
        if self.__board is None:
            return FlagResult.BOARD_NOT_GENERATED
        if (
            row < 0
            or row >= self.__rules.height
            or col < 0
            or col >= self.__rules.width
        ):
            return FlagResult.OFF_BOARD
        if self.game_over:
            return FlagResult.GAME_OVER
        if self.__revealed[row, col]:
            return FlagResult.ALREADY_REVEALED

        rules = self.__board.rules

        if flags is None:
            # increment flag up to max count,
            # or set back to 0 if it would go above
            self.__flags[row, col] = (self.__flags[row, col] + 1) % (
                rules.max_mines_per_tile + 1
            )
        elif flags < 0 or flags > rules.max_mines_per_tile:
            return FlagResult.INVALID_FLAG_COUNT
        else:
            self.__flags[row, col] = flags

        return FlagResult.SUCCESS

    def observe(self) -> Observation:
        """Get the player's view of the game.

        Returns:
            Observation: What the player can see in the current game.
        """
        shape = (self.__rules.height, self.__rules.width)

        if self.__board is None:
            # -1 for hidden clues
            visible_clues = np.full(shape, HIDDEN_CLUE, dtype=int)
        else:
            visible_clues = np.where(
                self.__revealed, self.__board.clues, HIDDEN_CLUE
            )

        visible_flags = self.__flags.copy()

        # make both read-only so an agent can't accidentally modify them
        visible_clues.flags.writeable = False
        visible_flags.flags.writeable = False

        return Observation(
            rules=self.__rules,
            clues=visible_clues,
            flags=visible_flags,
            mines_remaining=self.mines_remaining,
            status=self.__status,
        )

    @property
    def rules(self) -> Rules:
        """Get the rules used to generate the board.

        Returns:
            Rules: The rules used to generate the board.
        """
        return self.__rules

    @property
    def seed(self) -> int:
        """Get the seed used to generate the board.

        Returns:
            int: The seed used to generate the board.
        """
        return self.__seed

    @property
    def safe_zone_radius(self) -> int:
        """Get the initial safe zone radius.

        Returns:
            int: The initial safe zone radius.
        """
        return self.__safe_zone_radius

    @property
    def status(self) -> GameStatus:
        """Get the status of the game.

        Returns:
            GameStatus: The status of the game.
        """
        return self.__status

    @property
    def game_over(self) -> bool:
        """Check if the game is over.

        Returns:
            bool: True if the game is over, False otherwise.
        """
        return self.__status in (GameStatus.WON, GameStatus.LOST)

    @property
    def initial_guess(self) -> tuple[int, int] | None:
        """Get the initial guess for the first move.

        Returns `None` if the board has not been generated yet (no guesses).

        Returns:
            tuple[int, int] | None: The initial guess for the first move.
        """
        return self.__board.safe_cell if self.__board is not None else None

    @property
    def mines_remaining(self) -> int:
        """Get the number of mines remaining in the board.

        Returns:
            int: The number of mines remaining in the board.
        """
        return self.__rules.total_mines - int(self.__flags.sum())

    def __flood_fill(self, row: int, col: int) -> None:
        assert self.__board is not None

        queue = deque([(row, col)])
        while len(queue) > 0:
            r, c = queue.popleft()
            for nr, nc in get_neighbors((r, c), self.__board.counts):
                if not self.__revealed[nr, nc] and not self.__flags[nr, nc]:
                    # reveal each neighbor
                    self.__revealed[nr, nc] = True
                    # if the neighbor's clue is 0, reveal it's neighbors
                    if self.__board.clues[nr, nc] == 0:
                        queue.append((nr, nc))

    def __win_check(self) -> bool:
        if int(self.__revealed.sum()) == self.__safe_cells:
            self.__status = GameStatus.WON
        return self.__status == GameStatus.WON

    def __cell_to_str(
        self, row: int, col: int, clue: int, flags: int, show_mines: bool
    ) -> str:
        if self.__board is None:
            # all unrevealed
            return "#"
        if show_mines and self.__board.counts[row, col] > 0:
            # show X on exploded mine
            return (
                "X"
                if self.__exploded_cell == (row, col)
                else f"*{self.__board.counts[row, col]}"
            )
        if clue != HIDDEN_CLUE:
            return str(clue) if clue > 0 else "."
        if flags > 0:
            return f"F{flags}"
        # unrevealed
        return "#"

    def __str__(self) -> str:
        obs = self.observe()
        show_mines = (
            self.__status == GameStatus.LOST and self.__board is not None
        )

        cells = []
        for row_i, (clue_row, flag_row) in enumerate(zip(obs.clues, obs.flags)):
            row_cells = []
            for col_i, (clue, flag_count) in enumerate(zip(clue_row, flag_row)):
                row_cells.append(
                    self.__cell_to_str(
                        row_i, col_i, clue, flag_count, show_mines
                    )
                )
            cells.append(row_cells)
        return format_grid(cells)
