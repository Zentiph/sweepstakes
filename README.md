# Sweepstakes

Comparing AI agents on Minesweeper and its variants.

## Abstract

Minesweeper is a single-player puzzle that combines constraint satisfaction with decision-making under uncertainty. Each revealed number constrains its unrevealed neighbors. Sometimes those constraints determine which cells are safe, and sometimes a guess is unavoidable. Sweepstakes builds and compares AI agents that play Minesweeper on both the standard game and its variants, such as mine stacking, where a single tile can hold up to a determined number of mines and clues count total mines rather than mined tiles.

The project compares three approaches of increasing sophistication:

- **Rule-based baseline:** local deduction rules, with random guessing when no rule applies.
- **CSP agent:** backtracking search with forward checking and constraint propagation over the board's frontier.
- **Probabilistic CSP agent:** exact per-cell mine probabilities from enumerated configurations, with Monte Carlo sampling for large frontiers.

Agents are evaluated on large sets of seeded boards across difficulty levels and variants. They are compared on win rate, percentage of the board cleared, forced guesses per game, nodes/backtracks explored, and time per move.

## Developer

- Gavin Borne ([@Zentiph](https://github.com/Zentiph))

## Repository Structure

```
sweepstakes/
├── code/          # Game engine, agents, experiments, and visualizer
├── data/          # Generated boards, seeds, and experiment results
├── resources/     # References, project notes, and presentation slides
├── mypy.ini       # Type checker settings
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+

### Installation

```bash
git clone https://github.com/Zentiph/sweepstakes.git
cd sweepstakes
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e code
```

### Usage

```bash
python -m sweepstakes
```

The CLI asks whether to play a game yourself or watch an agent play one, then asks for the board:

- Width, height, and total mines.
- Max mines per tile (how many mines can stack on one tile). Use 1 for standard Minesweeper. Clues count total mines, not mined tiles.
- Seed: a non-negative board seed. The same rules, seed, and first reveal always give the same board.
- Safe zone radius: the first reveal is always safe, along with every cell within this many cells of it. Boards whose mines don't fit around a safe zone are rejected.

After a game ends, the CLI asks whether to play again, so a session can hold any number of games.

#### Playing

| Command           | Effect                                                    |
| ----------------- | --------------------------------------------------------- |
| `r row col`       | Reveal a cell. Revealing a 0 also reveals its neighbors.  |
| `f row col`       | Cycle a cell's flags from 0 up to the max mines per tile. |
| `f row col count` | Set a cell's flag count.                                  |
| `h`               | Show the commands and key.                                |
| `a`               | Abort the game and start a new one.                       |
| `q`               | Quit.                                                     |

Rows and columns start at 0, numbered along the board's edges. The mine counter is total mines minus flags placed, so it goes negative when cells are over-flagged.

| Symbol | Meaning |
| --- | --- |
| `n` | Clue: `n` mines in the neighboring cells |
| `.` | Clue of 0 |
| `#` | Hidden cell |
| `Fn` | Cell with `n` flags |
| `X` | The mine that was revealed (shown after a loss) |
| `*n` | Mine with `n` stacks (shown after a loss) |

#### Watching

Watching also asks for an agent from the registry (the available names are printed), an agent seed, and the pacing: a number of seconds to pause between steps, or blank to step with Enter. The agent's opening reveal is always the center cell.

Each step prints the agent's action, such as `reveal (3, 4) [guess]`, then the board. To stop a game partway through, type `a` (abort and start a new game) or `q` (quit) at the Enter prompt, or press Ctrl-C during a timed pause. When the game ends, a summary shows the result, the safe cells cleared out of the total, and the agent's reveals and guesses. Agents are also aborted after 20 invalid actions, or after too many actions in total.

#### Command line options

Any prompt can be skipped by passing its option, for every game in the session. Run `python -m sweepstakes -h` for the full list.

| Option | Skips the prompt for |
| --- | --- |
| `--mode {play,watch}` | Play or watch |
| `--width`, `--height`, `--mines`, `--max-stack` | The board rules |
| `--seed`, `--radius` | The board seed and safe zone radius |
| `--agent NAME`, `--agent-seed N` | The agent and its seed (watch only) |
| `--delay SECONDS` or `--step` | The pacing (watch only) |

For example, to watch the random agent on a standard beginner board with no prompts until the game ends:

```bash
python -m sweepstakes --mode watch --width 9 --height 9 --mines 10 --max-stack 1 \
    --seed 4 --radius 1 --agent random --agent-seed 4 --delay 0.5
```

Options that can never make a valid game, such as more mines than fit on the board, are rejected at startup.

#### Agents

| Name | Agent |
| --- | --- |
| `random` | Reveals a random hidden, unflagged cell every turn. The performance floor for other agents. |

### Development

Install the development tools instead of `requirements.txt`:

```bash
pip install -r requirements-dev.txt
pip install -e code
```

Run the tests, type checker, and formatter from `code/`. mypy reads its settings from `mypy.ini` at the repository root, so it also works from the root, as editors run it:

```bash
cd code
pytest
mypy .
ruff format .
```

## License

MIT. See [LICENSE](./LICENSE).