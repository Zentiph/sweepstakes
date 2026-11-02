"""A CLI for playing/observing sweepstakes."""

from collections.abc import Callable
from time import sleep

from .agents import AGENTS, Agent
from .experiments import play_game
from .game import Game
from .types import (
    Action,
    ActionKind,
    FlagResult,
    GameRecord,
    GameStatus,
    RevealResult,
    Rules,
)

__all__ = ["run"]

PARSE_ERROR = "Invalid input. Please try again."
COMMAND_ERROR = "Commands: r row col | f row col [count] | h | a | q"
STEP_PROMPT = "[Enter] next step | a: abort | q: quit "

HELP = """Commands:
r row col: Reveal a cell
f row col: Cycle a cell's flags
f row col count: Set a cell's flags
h: Show this help
a: Abort this game and start a new one
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


def play(game: Game) -> bool:
    """Read commands and apply them until the game ends.

    Args:
        game (Game): The game to play.

    Returns:
        bool: False if the player quit, True otherwise.
    """
    print_view(game)
    while not game.game_over:
        line = input("\n> ")
        command = line.strip().lower()
        if command == "q":
            return False
        if command == "a":
            game.abort()
            continue
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
    elif game.status == GameStatus.LOST:
        print("You lost!")
        print(f"\n{MINE_KEY}")
    else:
        print("Game aborted.")
        return True

    return ask_play_again()


def ask_play_again() -> bool:
    """Ask whether to start another game.

    Returns:
        bool: True to play again, False to quit.
    """
    return input("\nPlay again? [Y/n] ").strip().lower() in ("", "y", "yes")


def ask_choice(prompt: str, choices: list[str]) -> str:
    """Block the current thread until the input is one of the choices.

    Args:
        prompt (str): The prompt to ask.
        choices (list[str]): The allowed (lowercase) inputs.

    Returns:
        str: The chosen input.
    """
    while True:
        choice = input(prompt).strip().lower()
        if choice in choices:
            return choice
        print(PARSE_ERROR)


def ask_agent() -> type[Agent]:
    """Block the current thread until an agent is chosen from the registry.

    Returns:
        type[Agent]: The chosen agent class.
    """
    names = sorted(AGENTS)
    print("Agents:", ", ".join(names))
    return AGENTS[ask_choice("Agent: ", names)]


def ask_delay() -> float | None:
    """Block the current thread until a step pacing is chosen.

    Returns:
        float | None: The seconds between steps, or None to wait for Enter.
    """
    while True:
        line = input("Seconds between steps (blank to step with Enter): ")
        if not line.strip():
            return None
        try:
            delay = float(line)
            if delay >= 0:
                return delay
        except ValueError:
            pass
        print(PARSE_ERROR)


def describe_action(game: Game, action: Action | None) -> str:
    """Describe an agent's action.

    Args:
        game (Game): The game the action was taken in.
        action (Action | None): The action, or None for the opening reveal.

    Returns:
        str: The description, e.g. `reveal (3, 4) [guess]`.
    """
    if action is None:
        return f"reveal {game.initial_guess} [opening]"
    if action.kind == ActionKind.FLAG:
        return f"flag ({action.row}, {action.col}) to {action.flags}"
    guess = " [guess]" if action.is_guess else ""
    return f"reveal ({action.row}, {action.col}){guess}"


def print_summary(record: GameRecord) -> None:
    """Print a short summary of a watched game.

    Args:
        record (GameRecord): The record of the game.
    """
    print(
        f"\nResult: {record.status.name.lower()}",
        f"Cleared: {record.safe_cells_revealed}/{record.total_safe_cells}"
        + " safe cells",
        f"Reveals: {record.reveals}",
        f"Guesses: {record.guesses}",
        sep="\n",
    )
    if record.status == GameStatus.LOST:
        print(f"\n{MINE_KEY}")


def watch(rules: Rules) -> bool:
    """Set up a game for an agent and print each of its steps.

    The viewer can abort the game partway through: with `a` or `q` when
    stepping with Enter, or with Ctrl-C during a timed pause.

    Args:
        rules (Rules): The rules to use.

    Returns:
        bool: False if the viewer quit, True otherwise.
    """
    agent_cls = ask_agent()
    game = ask_game(rules)
    agent_seed = ask_until_int_and(
        "Agent seed: ", predicate=None, error=PARSE_ERROR
    )
    delay = ask_delay()
    quit_requested = False

    def on_step(game: Game, action: Action | None) -> None:
        nonlocal quit_requested
        print(f"\n{describe_action(game, action)}")
        print_view(game)
        if game.game_over:
            return

        if delay is not None:
            try:
                sleep(delay)
            except KeyboardInterrupt:
                game.abort()
            return

        command = input(STEP_PROMPT).strip().lower()
        if command in ("a", "q"):
            game.abort()
            quit_requested = command == "q"

    record = play_game(game, agent_cls(), agent_seed, on_step=on_step)
    print_summary(record)
    return not quit_requested and ask_play_again()


def run() -> None:
    """Run the CLI, setting up and playing or watching games until quit."""

    try:
        while True:
            mode = ask_choice(
                "Play or watch? [p/w, q to quit] ", ["p", "w", "q"]
            )
            if mode == "q":
                break

            rules = ask_rules()
            print("\nSelected rules:", rules, end="\n\n")

            if mode == "w":
                keep_going = watch(rules)
            else:
                game = ask_game(rules)
                print(f"\n{HELP}\n")
                keep_going = play(game)
            if not keep_going:
                break
            print()
    except (EOFError, KeyboardInterrupt):
        # end of input or Ctrl-C during any prompt
        print()
