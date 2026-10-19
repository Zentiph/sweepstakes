"""
Entrypoint for running sweepstakes.
"""

from sweepstakes.types import Board, Rules


def main() -> None:
    rules = Rules(width=10, height=10, total_mines=16, max_mines_per_tile=2)
    board = Board(rules=rules, seed=69420, safe_cell=(4, 4))

    print(board)


if __name__ == "__main__":
    main()
