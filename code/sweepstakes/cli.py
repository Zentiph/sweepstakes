"""A basic CLI for running/testing sweepstakes."""

from collections.abc import Callable

from .game import Game
from .types import FlagResult, GameStatus, RevealResult, Rules

__all__ = ["run"]

PARSE_ERROR = "Invalid input. Please try again."
COMMAND_ERROR = "Commands: r row col | f row col [count] | h | q"

HELP = """Commands:
r row col: Reveal a cell
f row col: Cycle a cell's flags
f row col count: Set a cell's flags
h: Show this help
q: Quit

Key:
n  = clue: n mines in the neighboring cells
.  = clue of 0
#  = hidden cell
Fn = cell with n flags"""
MINE_KEY = """Mine key:
X  = exploded mine
*n = mine with n stacks"""

REVEAL_ERRORS = {
    RevealResult.OFF_BOARD: "That cell is off the board.",
    RevealResult.ALREADY_REVEALED: "That cell is already revealed.",
    RevealResult.FLAGGED: "That cell is flagged. Unflag it first.",
    RevealResult.GAME_OVER: "The game is over.",
}
FLAG_ERRORS = {
    FlagResult.INVALID_FLAG_COUNT: "Invalid flag count for this board.",
    FlagResult.BOARD_NOT_GENERATED: "Reveal a cell before placing flags.",
    FlagResult.OFF_BOARD: "That cell is off the board.",
    FlagResult.ALREADY_REVEALED: "That cell is already revealed.",
    FlagResult.GAME_OVER: "The game is over.",
}


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


def ask_game(rules: Rules) -> Game:
    """Block the current thread until a valid game is created.

    Args:
        rules (Rules): The rules to use.

    Returns:
        Game: The created game.
    """
    game = None
    while game is None:
        seed = ask_until_int_and("Seed: ", predicate=None, error=PARSE_ERROR)
        safe_zone_radius = ask_until_int_and(
            "Safe zone radius: ",
            predicate=lambda x: x >= 0,
            error=PARSE_ERROR,
        )

        try:
            game = Game(rules, seed, safe_zone_radius)
        except ValueError as e:
            print(e)

    return game


def print_view(game: Game) -> None:
    """Print the player's view of the game and the mine counter.

    Args:
        game (Game): The game to print.
    """
    print(game)
    print(f"Mines remaining: {game.mines_remaining}")


def apply_command(game: Game, line: str) -> str | None:
    """Parse a command and apply it to the game.

    Args:
        game (Game): The game to apply the command to.
        line (str): The command, as `r row col` or `f row col [count]`.

    Returns:
        str | None: The error message, or None if the command was applied.
    """
    action, *raw_args = line.lower().split() or [""]
    try:
        args = [int(arg) for arg in raw_args]
    except ValueError:
        return COMMAND_ERROR

    if action == "r" and len(args) == 2:
        return REVEAL_ERRORS.get(game.reveal(args[0], args[1]))
    if action == "f" and len(args) == 2:
        return FLAG_ERRORS.get(game.flag(args[0], args[1]))
    if action == "f" and len(args) == 3:
        return FLAG_ERRORS.get(game.flag(args[0], args[1], flags=args[2]))
    return COMMAND_ERROR


def play(game: Game) -> None:
    """Read commands and apply them until the game ends or the player quits.

    Args:
        game (Game): The game to play.
    """
    print_view(game)
    while game.status == GameStatus.IN_PROGRESS:
        try:
            line = input("\n> ")
        except EOFError:
            return
        command = line.strip().lower()
        if command == "q":
            return
        if command in ("h", "help"):
            print(HELP)
            continue

        error = apply_command(game, line)
        if error is None:
            print_view(game)
        else:
            print(error)

    if game.status == GameStatus.WON:
        print("You won!")
    else:
        print("You lost!")
        print(f"\n{MINE_KEY}")


def run() -> None:
    """Run the CLI, asking for input to set up a game, then playing it."""

    rules = ask_rules()
    print("\nSelected rules:", rules, end="\n\n")

    game = ask_game(rules)
    print(f"\n{HELP}\n")
    play(game)
