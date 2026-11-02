"""Tests for the command line interface."""

from collections.abc import Iterator

import numpy as np
import pytest

from sweepstakes import __main__
from sweepstakes.agents import AGENTS
from sweepstakes.cli import (
    COMMAND_ERROR,
    FLAG_ERRORS,
    HELP,
    MINE_KEY,
    PARSE_ERROR,
    REVEAL_ERRORS,
    apply_command,
    ask_choice,
    describe_action,
    parse_args,
    pause,
    run,
)
from sweepstakes.game import Board, Game
from sweepstakes.types import (
    Action,
    ActionKind,
    FlagResult,
    GameStatus,
    RevealResult,
    Rules,
)

BOARD = ["--width", "9", "--height", "9", "--mines", "10", "--max-stack", "1"]
# a 3x3 board where revealing the center is an instant win
TINY = ["--width", "3", "--height", "3", "--mines", "8", "--max-stack", "1"]
TINY_GAME = [*TINY, "--seed", "0", "--radius", "0"]
WATCH_GAME = [*BOARD, "--seed", "4", "--radius", "1", "--agent", "random"]


def feed(monkeypatch: pytest.MonkeyPatch, *lines: str) -> Iterator[str]:
    """Answer `input()` prompts with the given lines, then end of input."""
    answers = iter(lines)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", fake_input)
    return answers


def test_parse_args_defaults_to_asking_everything():
    args = parse_args([])

    assert args.mode is None
    assert args.width is None
    assert args.seed is None
    assert args.agent is None
    assert args.delay is None
    assert not args.step


def test_parse_args_reads_presets():
    args = parse_args(
        ["--mode", "watch", *BOARD, "--seed", "4", "--radius", "1"]
        + ["--agent", "random", "--agent-seed", "2", "--delay", "0.5"]
    )

    assert args.mode == "watch"
    assert (args.width, args.height, args.mines, args.max_stack) == (
        9,
        9,
        10,
        1,
    )
    assert (args.seed, args.radius) == (4, 1)
    assert (args.agent, args.agent_seed, args.delay) == ("random", 2, 0.5)


@pytest.mark.parametrize(
    "argv",
    [
        ["--width", "0"],
        ["--mines", "-1"],
        ["--seed", "-1"],
        ["--agent-seed", "-1"],
        ["--radius", "-1"],
        ["--delay", "-1"],
        ["--delay", "1", "--step"],
        ["--mode", "fly"],
        ["--agent", "nobody"],
        # presets that can never make a game
        ["--width", "1", "--height", "1", "--mines", "2", "--max-stack", "1"],
        ["--width", "1", "--height", "1", "--mines", "1", "--max-stack", "1"],
        [*BOARD, "--mines", "80", "--radius", "1"],
    ],
)
def test_parse_args_rejects_bad_presets(argv: list[str]):
    with pytest.raises(SystemExit):
        parse_args(argv)


def test_ask_choice_matches_case_insensitively(monkeypatch: pytest.MonkeyPatch):
    feed(monkeypatch, "nope", "RANDOM")

    assert ask_choice("Agent: ", ["Random"]) == "Random"


def test_describe_action():
    game = Game(Rules(9, 9, 10, 1), 0)
    game.reveal(4, 4)

    assert describe_action(game, None) == "reveal (4, 4) [opening]"
    assert (
        describe_action(game, Action(ActionKind.REVEAL, 3, 4, is_guess=True))
        == "reveal (3, 4) [guess]"
    )
    assert (
        describe_action(game, Action(ActionKind.REVEAL, 3, 4))
        == "reveal (3, 4)"
    )
    assert (
        describe_action(game, Action(ActionKind.FLAG, 1, 2, flags=1))
        == "flag (1, 2) to 1"
    )


def test_run_watch_with_presets_needs_no_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    feed(monkeypatch, "n")
    run(
        ["--mode", "watch", *BOARD, "--seed", "4", "--radius", "1"]
        + ["--agent", "random", "--agent-seed", "4", "--delay", "0"]
    )

    out = capsys.readouterr().out
    assert "reveal (4, 4) [opening]" in out
    assert "Result: lost" in out
    assert "Reveals: 7" in out


def test_run_rejects_negative_seed_prompt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "-1", "0", "1", "q")
    run(["--mode", "play", *BOARD])

    assert "Invalid input" in capsys.readouterr().out
    assert next(answers, None) is None


def test_run_reasks_rules_when_preset_radius_does_not_fit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    # 3x3 board with 1 mine leaves no room around a radius 1 safe zone
    answers = feed(monkeypatch, "3", "3", "1", "1", "9", "9", "10", "1", "q")
    run(["--mode", "play", "--seed", "0", "--radius", "1"])

    out = capsys.readouterr().out
    assert "Not enough room" in out
    assert out.count("Selected rules") == 2
    assert next(answers, None) is None


def test_run_watch_abort_then_quit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    feed(monkeypatch, "w", "", "a", "w", "q")
    run(
        [*BOARD, "--seed", "4", "--radius", "1"]
        + ["--agent", "random"]
        + ["--agent-seed", "4", "--step"]
    )

    out = capsys.readouterr().out
    assert out.count("Result: aborted") == 2
    assert "Play again" not in out


def test_registry_names_match_agents():
    for name, agent_cls in AGENTS.items():
        assert agent_cls.name == name


@pytest.fixture
def started() -> Game:
    game = Game(Rules(9, 9, 10, 1), 4)
    game.reveal(4, 4)
    return game


@pytest.mark.parametrize(
    ("line", "error"),
    [
        ("r 8 1", None),
        ("R 8 1", None),
        ("  r   8   1  ", None),
        ("f 0 5", None),
        ("f 0 5 1", None),
        ("r 4 4", REVEAL_ERRORS[RevealResult.ALREADY_REVEALED]),
        ("r 9 0", REVEAL_ERRORS[RevealResult.OFF_BOARD]),
        ("f 0 5 2", FLAG_ERRORS[FlagResult.INVALID_FLAG_COUNT]),
        ("f -1 0", FLAG_ERRORS[FlagResult.OFF_BOARD]),
        ("", COMMAND_ERROR),
        ("x 0 0", COMMAND_ERROR),
        ("r 0", COMMAND_ERROR),
        ("r 0 0 0", COMMAND_ERROR),
        ("f 0 0 0 0", COMMAND_ERROR),
        ("r a b", COMMAND_ERROR),
    ],
)
def test_apply_command(started: Game, line: str, error: str | None):
    assert apply_command(started, line) == error


def test_apply_command_flag_before_first_reveal():
    game = Game(Rules(9, 9, 10, 1), 4)

    assert (
        apply_command(game, "f 0 0")
        == FLAG_ERRORS[FlagResult.BOARD_NOT_GENERATED]
    )


def test_apply_command_flag_cycles(started: Game):
    apply_command(started, "f 0 5")

    assert started.observe().flags[0, 5] == 1


@pytest.mark.parametrize(("line", "stop"), [("", ""), ("x", ""), ("a", "a")])
def test_pause_waits_for_enter(
    monkeypatch: pytest.MonkeyPatch, started: Game, line: str, stop: str
):
    feed(monkeypatch, line)

    assert pause(started, None) == stop
    assert started.game_over == (stop == "a")


def test_pause_quit_aborts(monkeypatch: pytest.MonkeyPatch, started: Game):
    feed(monkeypatch, "Q")

    assert pause(started, None) == "q"
    assert started.status == GameStatus.ABORTED


def interrupt(*args: object) -> str:
    raise KeyboardInterrupt


def test_pause_ctrl_c_at_enter_prompt_aborts(
    monkeypatch: pytest.MonkeyPatch, started: Game
):
    monkeypatch.setattr("builtins.input", interrupt)

    assert pause(started, None) == "a"
    assert started.status == GameStatus.ABORTED


def test_pause_sleeps_for_delay(monkeypatch: pytest.MonkeyPatch, started: Game):
    slept: list[float] = []
    monkeypatch.setattr("sweepstakes.cli.sleep", slept.append)

    assert pause(started, 0.25) == ""
    assert slept == [0.25]
    assert not started.game_over


def test_pause_ctrl_c_during_sleep_aborts(
    monkeypatch: pytest.MonkeyPatch, started: Game
):
    monkeypatch.setattr("sweepstakes.cli.sleep", interrupt)

    assert pause(started, 1) == "a"
    assert started.status == GameStatus.ABORTED


def test_run_play_win(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "h", "zzz", "r 1 1", "n")
    run(["--mode", "play", *TINY_GAME])

    out = capsys.readouterr().out
    assert out.count(HELP) == 2  # at the start, and for h
    assert COMMAND_ERROR in out
    assert "You won!" in out
    assert MINE_KEY not in out
    assert next(answers, None) is None


def test_run_play_loss_shows_mines(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    board = Board(Rules(9, 9, 10, 1), 4, (4, 4))
    mine_row, mine_col = (int(i) for i in np.argwhere(board.counts > 0)[0])
    feed(monkeypatch, "r 4 4", f"r {mine_row} {mine_col}", "n")
    run(["--mode", "play", *BOARD, "--seed", "4", "--radius", "1"])

    out = capsys.readouterr().out
    assert "You lost!" in out
    assert MINE_KEY in out
    assert " X" in out


def test_run_play_again_starts_a_new_game(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "r 1 1", "y", "r 1 1", "N")
    run(["--mode", "play", *TINY_GAME])

    assert capsys.readouterr().out.count("You won!") == 2
    assert next(answers, None) is None


def test_run_play_abort_starts_a_new_game(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "a", "q")
    run(["--mode", "play", *TINY_GAME])

    out = capsys.readouterr().out
    assert "Game aborted." in out
    assert out.count("Selected rules") == 2
    assert next(answers, None) is None


def test_run_asks_mode_until_valid(monkeypatch: pytest.MonkeyPatch, capsys):
    answers = feed(monkeypatch, "x", "Q")
    run([])

    assert PARSE_ERROR in capsys.readouterr().out
    assert next(answers, None) is None


def test_run_mode_prompt_starts_each_game(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "p", "r 1 1", "y", "q")
    run(TINY_GAME)

    assert "You won!" in capsys.readouterr().out
    assert next(answers, None) is None


def test_run_end_of_input_exits_cleanly(monkeypatch: pytest.MonkeyPatch):
    feed(monkeypatch)

    run(["--mode", "play"])


def test_run_ctrl_c_exits_cleanly(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("builtins.input", interrupt)

    run([])


def test_run_reasks_invalid_rules(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(
        monkeypatch,
        *[
            "abc",
            "0",
            "1",
            "1",
            "5",
            "1",
        ],  # not a number, too small, too many mines
        *["3", "3", "8", "1"],
        *["0", "0"],  # seed and radius
        "q",
    )
    run(["--mode", "play"])

    out = capsys.readouterr().out
    assert out.count(PARSE_ERROR) == 2
    assert "Total mines must be" in out
    assert out.count("Selected rules") == 1
    assert next(answers, None) is None


def test_run_reasks_prompted_radius_that_does_not_fit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "0", "1", "0", "0", "q")
    run(["--mode", "play", *TINY[:4], "--mines", "1", "--max-stack", "1"])

    out = capsys.readouterr().out
    assert "Not enough room" in out
    assert out.count("Selected rules") == 1
    assert next(answers, None) is None


def test_run_watch_prompts_for_agent_and_pacing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(
        monkeypatch,
        *["nope", "Random"],  # agent
        "4",  # agent seed
        *["x", "-1", ""],  # pacing: blank steps with Enter
        *["", "q"],  # one step, then quit
    )
    run(["--mode", "watch", *BOARD, "--seed", "4", "--radius", "1"])

    out = capsys.readouterr().out
    assert "Agents: random" in out
    assert out.count(PARSE_ERROR) == 3
    assert out.count("[guess]") == 1
    assert "Result: aborted" in out
    assert next(answers, None) is None


def test_run_watch_play_again(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    answers = feed(monkeypatch, "y", "n")
    run(["--mode", "watch", *WATCH_GAME, "--agent-seed", "4", "--delay", "0"])

    assert capsys.readouterr().out.count("Result: lost") == 2
    assert next(answers, None) is None


def test_run_watch_win_hides_mine_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    feed(monkeypatch, "n")
    run(
        ["--mode", "watch", *TINY_GAME, "--agent", "random"]
        + ["--agent-seed", "0", "--delay", "0"]
    )

    out = capsys.readouterr().out
    assert "Result: won" in out
    assert "Cleared: 1/1 safe cells" in out
    assert MINE_KEY not in out


def test_main_reads_command_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr("sys.argv", ["sweepstakes", "-h"])

    with pytest.raises(SystemExit) as exit_info:
        __main__.main()

    assert exit_info.value.code == 0
    assert "--mode" in capsys.readouterr().out


def test_run_watch_prompted_delay(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    slept: list[float] = []
    monkeypatch.setattr("sweepstakes.cli.sleep", slept.append)
    answers = feed(monkeypatch, "0.5", "n")
    run(["--mode", "watch", *WATCH_GAME, "--agent-seed", "4"])

    assert "Result: lost" in capsys.readouterr().out
    assert slept and set(slept) == {0.5}
    assert next(answers, None) is None
