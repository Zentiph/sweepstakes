"""
Entrypoint for running sweepstakes.
"""

from sweepstakes import run_cli


def main() -> None:
    """Run the CLI with the command line arguments."""
    run_cli()


if __name__ == "__main__":
    main()
