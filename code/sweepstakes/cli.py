"""A basic CLI for running/testing sweepstakes."""

from collections.abc import Callable

from .types import Board, Rules

__all__ = ["run"]


def ask_until_int_and(
    prompt: str, *, predicate: Callable[[int], bool] | None, error: str = ""
) -> int:
    """Block the current thread until the input from the prompt is a valid int.

    Args:
        prompt (str): The prompt to ask.
        predicate (Callable[[int], bool] | None, optional): The predicate to check the input against. Defaults to None.
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


def run() -> None:
    """Run the CLI, asking for input to generate a board, then print it."""
    parse_error = "Invalid input. Please try again."

    width = ask_until_int_and(
        "Board width: ", predicate=lambda x: x > 0, error=parse_error
    )
    height = ask_until_int_and(
        "Board height: ", predicate=lambda x: x > 0, error=parse_error
    )
    total_mines = ask_until_int_and(
        "Total mines: ", predicate=lambda x: x >= 0, error=parse_error
    )
    max_mines_per_tile = ask_until_int_and(
        "Max mines per tile: ", predicate=lambda x: x > 0, error=parse_error
    )

    rules = Rules(width, height, total_mines, max_mines_per_tile)

    print("\nSelected rules:", rules, end="\n\n")

    seed = ask_until_int_and("Seed: ", predicate=None)
    safe_x = ask_until_int_and(
        "Safe cell x: ",
        predicate=lambda x: x >= 0 and x < width,
        error=parse_error,
    )
    safe_y = ask_until_int_and(
        "Safe cell y: ",
        predicate=lambda x: x >= 0 and x < height,
        error=parse_error,
    )

    safe_cell = (safe_y, safe_x)

    safe_zone_radius = ask_until_int_and(
        "Safe zone radius: ", predicate=lambda x: x >= 0, error=parse_error
    )

    board = Board(rules, seed, safe_cell, safe_zone_radius)

    print("\nGenerated board:")
    print(board)
    print(
        "\nKey:",
        "Number: Clue",
        "Dot (.): Safe/0 clue",
        "Star (*): Mine & stack count",
        sep="\n",
    )
