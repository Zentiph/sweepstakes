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
├── requirements.txt
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
```

### Usage

> WIP. Run instructions will be added as the project develops.

## License

MIT. See [LICENSE](./LICENSE).