"""A CLI for playing/observing sweepstakes."""

import argparse
from collections.abc import Callable, Sequence
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


def at_least(minimum: int) -> Callable[[str], int]:
    """Make an argparse type that parses an int of at least `minimum`.

    Args:
        minimum (int): The smallest allowed value.

    Returns:
        Callable[[str], int]: The argparse type.
    """

    def parse(text: str) -> int:
        value = int(text)
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be at least {minimum}")
        return value

    return parse


def non_negative_float(text: str) -> float:
    """Parse a non-negative float for argparse.

    Args:
        text (str): The text to parse.

    Returns:
        float: The parsed float.
    """
    value = float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the command line options.

    Every option is optional. Any option given skips its prompt, for every
    game in the session.

    Args:
        argv (Sequence[str] | None, optional): The arguments to parse.
        Defaults to None, which reads `sys.argv`.

    Returns:
        argparse.Namespace: The parsed options, None for any left out.
    """
    parser = argparse.ArgumentParser(
        prog="python -m sweepstakes",
        description="Play Minesweeper, or watch an agent play it. "
        + "Options skip their prompts; anything left out is asked for.",
    )
    parser.add_argument("--mode", choices=["play", "watch"])

    board = parser.add_argument_group("board")
    board.add_argument("--width", type=at_least(1))
    board.add_argument("--height", type=at_least(1))
    board.add_argument("--mines", type=at_least(0), help="total mines")
    board.add_argument(
        "--max-stack", type=at_least(1), help="max mines per tile"
    )
    board.add_argument("--seed", type=at_least(0), help="board seed")
    board.add_argument("--radius", type=at_least(0), help="safe zone radius")

    watch = parser.add_argument_group("watch mode")
    watch.add_argument("--agent", choices=sorted(AGENTS))
    watch.add_argument("--agent-seed", type=at_least(0))
    pacing = watch.add_mutually_exclusive_group()
    pacing.add_argument(
        "--delay",
        type=non_negative_float,
        metavar="SECONDS",
        help="pause between steps",
    )
    pacing.add_argument(
        "--step", action="store_true", help="press Enter between steps"
    )

    args = parser.parse_args(argv)
    check_presets(parser, args)
    return args


def check_presets(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Exit with an error if the preset board options can never make a game.

    Without this, the prompts for the remaining options would loop forever.

    Args:
        parser (argparse.ArgumentParser): The parser to report errors with.
        args (argparse.Namespace): The parsed options.
    """
    values = (args.width, args.height, args.mines, args.max_stack)
    if None in values:
        return  # the prompted values can still fix the rules

    try:
        rules = Rules(*values)
        # a prompted radius can always be 0
        Game(rules, 0, args.radius if args.radius is not None else 0)
    except ValueError as e:
        parser.error(str(e))


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


def preset_or_ask(
    preset: int | None, prompt: str, predicate: Callable[[int], bool]
) -> int:
    """Use a preset value, or ask for one if there is none.

    Args:
        preset (int | None): The preset value from the command line.
        prompt (str): The prompt to ask.
        predicate (Callable[[int], bool]): The predicate to check the input against.

    Returns:
        int: The preset or asked value.
    """
    if preset is not None:
        return preset
    return ask_until_int_and(prompt, predicate=predicate, error=PARSE_ERROR)


def ask_rules(args: argparse.Namespace) -> Rules:
    """Block the current thread until a valid set of rules is created.

    Args:
        args (argparse.Namespace): The command line options.

    Returns:
        Rules: The created rules.
    """
    while True:
        width = preset_or_ask(args.width, "Board width: ", lambda x: x > 0)
        height = preset_or_ask(args.height, "Board height: ", lambda x: x > 0)
        total_mines = preset_or_ask(
            args.mines, "Total mines: ", lambda x: x >= 0
        )
        max_mines_per_tile = preset_or_ask(
            args.max_stack, "Max mines per tile: ", lambda x: x > 0
        )

        try:
            return Rules(width, height, total_mines, max_mines_per_tile)
        except ValueError as e:
            print(e)


def ask_game(rules: Rules, args: argparse.Namespace) -> Game | None:
    """Ask for the seed and safe zone radius, and create a game.

    Args:
        rules (Rules): The rules to use.
        args (argparse.Namespace): The command line options.

    Returns:
        Game | None: The created game, or None if the rules don't fit.
    """
    seed = preset_or_ask(args.seed, "Seed: ", lambda x: x >= 0)
    safe_zone_radius = preset_or_ask(
        args.radius, "Safe zone radius: ", lambda x: x >= 0
    )

    try:
        return Game(rules, seed, safe_zone_radius)
    except ValueError as e:
        print(e)
        return None


def ask_setup(args: argparse.Namespace) -> Game:
    """Block the current thread until the rules and a valid game are created.

    Args:
        args (argparse.Namespace): The command line options.

    Returns:
        Game: The created game.
    """
    while True:
        rules = ask_rules(args)
        print("\nSelected rules:", rules, end="\n\n")

        while True:
            game = ask_game(rules, args)
            if game is not None:
                return game
            if args.radius is not None:
                break  # the preset radius doesn't fit, so change the rules


def ask_mode() -> str:
    """Ask whether to play, watch, or quit.

    Returns:
        str: "play", "watch", or "quit".
    """
    choice = ask_choice("Play or watch? [p/w, q to quit] ", ["p", "w", "q"])
    return {"p": "play", "w": "watch", "q": "quit"}[choice]


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

    The input is matched case-insensitively.

    Args:
        prompt (str): The prompt to ask.
        choices (list[str]): The allowed inputs.

    Returns:
        str: The chosen input, as written in `choices`.
    """
    by_lowercase = {choice.lower(): choice for choice in choices}
    while True:
        choice = input(prompt).strip().lower()
        if choice in by_lowercase:
            return by_lowercase[choice]
        print(PARSE_ERROR)


def ask_agent() -> type[Agent]:
    """Block the current thread until an agent is chosen from the registry.

    Returns:
        type[Agent]: The chosen agent class.
    """
    names = sorted(AGENTS)
    print("Agents:", ", ".join(names))
    return AGENTS[ask_choice("Agent: ", names)]


def ask_delay(args: argparse.Namespace) -> float | None:
    """Block the current thread until a step pacing is chosen.

    Args:
        args (argparse.Namespace): The command line options.

    Returns:
        float | None: The seconds between steps, or None to wait for Enter.
    """
    if args.step:
        return None
    if args.delay is not None:
        return float(args.delay)

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


def pause(game: Game, delay: float | None) -> str:
    """Wait between watched steps, aborting the game if the viewer asks.

    Args:
        game (Game): The game being watched.
        delay (float | None): The seconds to wait, or None to wait for Enter.

    Returns:
        str: "q" if the viewer quit, "a" if they aborted, "" otherwise.
    """
    try:
        if delay is not None:
            sleep(delay)
            return ""
        command = input(STEP_PROMPT).strip().lower()
    except KeyboardInterrupt:
        print()
        command = "a"

    if command not in ("a", "q"):
        return ""
    game.abort()
    return command


def watch(game: Game, args: argparse.Namespace) -> bool:
    """Have an agent play a game, printing each of its steps.

    The viewer can abort the game partway through: with `a` or `q` when
    stepping with Enter, or with Ctrl-C during any pause.

    Args:
        game (Game): The game for the agent to play.
        args (argparse.Namespace): The command line options.

    Returns:
        bool: False if the viewer quit, True otherwise.
    """
    agent_cls = AGENTS[args.agent] if args.agent else ask_agent()
    agent_seed = preset_or_ask(
        args.agent_seed, "Agent seed: ", lambda x: x >= 0
    )
    delay = ask_delay(args)
    viewer_stop = ""

    def on_step(game: Game, action: Action | None) -> None:
        nonlocal viewer_stop
        print(f"\n{describe_action(game, action)}")
        print_view(game)
        if not game.game_over:
            viewer_stop = pause(game, delay)

    record = play_game(game, agent_cls(), agent_seed, on_step=on_step)
    print_summary(record)
    if viewer_stop:
        # like play mode: abort starts a new game, quit ends the session
        return viewer_stop == "a"
    return ask_play_again()


def run(argv: Sequence[str] | None = None) -> None:
    """Run the CLI, setting up and playing or watching games until quit.

    Args:
        argv (Sequence[str] | None, optional): The command line arguments.
        Defaults to None, which reads `sys.argv`.
    """
    args = parse_args(argv)

    try:
        while True:
            mode = args.mode or ask_mode()
            if mode == "quit":
                break

            game = ask_setup(args)
            if mode == "watch":
                keep_going = watch(game, args)
            else:
                print(f"\n{HELP}\n")
                keep_going = play(game)
            if not keep_going:
                break
            print()
    except (EOFError, KeyboardInterrupt):
        # end of input or Ctrl-C during any prompt
        print()
