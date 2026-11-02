"""Tests for the command line interface."""

from collections.abc import Iterator

import pytest

from sweepstakes.agents import AGENTS
from sweepstakes.cli import ask_choice, describe_action, parse_args, run
from sweepstakes.game import Game
from sweepstakes.types import Action, ActionKind, Rules

BOARD = ["--width", "9", "--height", "9", "--mines", "10", "--max-stack", "1"]


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
