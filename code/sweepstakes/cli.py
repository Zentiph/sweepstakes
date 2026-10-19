"""A basic CLI for running/testing sweepstakes."""

from collections.abc import Callable

from .game import Board
from .types import Rules

__all__ = ["run"]

PARSE_ERROR = "Invalid input. Please try again."


def ask_until_int_and(
    prompt: str, *, predicate: Callable[[int], bool] | None, error: str = ""
) -> int:
    """Block the current thread until the input from the prompt is a valid int.

    Args:
        prompt (str): The prompt to ask.
        predicate (Callable[[int], bool] | None): The predicate to check the input against.
        error (str, optional): The error message to print on failure. Defaults to "".

    Returns:
        int: The converted int.
    """
    while True:
        try:
            value = int(input(prompt))
            if not predicate:
                return value
            if predicate(value):
                return value
        except ValueError:
            pass

        if error:
            print(error)


def ask_rules() -> Rules:
    """Block the current thread until a valid set of rules is created.

    Returns:
        Rules: The created rules.
    """
    rules = None
    while rules is None:
        width = ask_until_int_and(
            "Board width: ", predicate=lambda x: x > 0, error=PARSE_ERROR
        )
        height = ask_until_int_and(
            "Board height: ", predicate=lambda x: x > 0, error=PARSE_ERROR
        )
        total_mines = ask_until_int_and(
            "Total mines: ", predicate=lambda x: x >= 0, error=PARSE_ERROR
        )
        max_mines_per_tile = ask_until_int_and(
            "Max mines per tile: ", predicate=lambda x: x > 0, error=PARSE_ERROR
        )

        try:
            rules = Rules(width, height, total_mines, max_mines_per_tile)
        except ValueError as e:
            print(e)

    return rules


def ask_board(rules: Rules) -> Board:
    """Block the current thread until a valid board is created.

    Args:
        rules (Rules): The rules to use.

    Returns:
        Board: The created board.
    """
    board = None
    while board is None:
        try:
            seed = ask_until_int_and(
                "Seed: ", predicate=None, error=PARSE_ERROR
            )
            safe_x = ask_until_int_and(
                "Safe cell x: ",
                predicate=lambda x: 0 <= x < rules.width,
                error=PARSE_ERROR,
            )
            safe_y = ask_until_int_and(
                "Safe cell y: ",
                predicate=lambda x: 0 <= x < rules.height,
                error=PARSE_ERROR,
            )

            safe_cell = (safe_y, safe_x)

            safe_zone_radius = ask_until_int_and(
                "Safe zone radius: ",
                predicate=lambda x: x >= 0,
                error=PARSE_ERROR,
            )

            board = Board(rules, seed, safe_cell, safe_zone_radius)
        except ValueError as e:
            print(e)

    return board


def run() -> None:
    """Run the CLI, asking for input to generate a board, then print it."""

    rules = ask_rules()
    print("\nSelected rules:", rules, end="\n\n")

    board = ask_board(rules)
    print("\nGenerated board:")
    print(board)
    print(
        "\nKey:",
        "Number: Clue",
        "Dot (.): Safe/0 clue",
        "Star (*): Mine & stack count",
        sep="\n",
    )
