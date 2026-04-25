"""CLI entry point for the quarterly processing pipeline."""

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.service import process_quarterly


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run quarterly session processing and print aggregated stats.",
    )
    parser.add_argument(
        "--sessions-root",
        type=Path,
        default=Path("quarterly_output"),
        help="Directory containing .mdr session files (default: quarterly_output).",
    )
    parser.add_argument(
        "--no-strict-entry-keys",
        action="store_true",
        help="Disable strict entry key validation.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print output as JSON.",
    )
    return parser


def _print_human(stats_dict: dict[str, object], sessions_root: Path, strict_entry_keys: bool) -> None:
    print("Quarterly processing completed")
    print(f"Sessions root: {sessions_root}")
    print(f"Strict entry keys: {strict_entry_keys}")
    print("")

    print("Main metrics")
    print(f"- files_seen: {stats_dict['files_seen']}")
    print(f"- files_used: {stats_dict['files_used']}")
    print(f"- sessions_valid: {stats_dict['sessions_valid']}")
    print(f"- sessions_invalid: {stats_dict['sessions_invalid']}")
    print(f"- entries_seen: {stats_dict['entries_seen']}")
    print(f"- entries_valid: {stats_dict['entries_valid']}")
    print(f"- entries_invalid: {stats_dict['entries_invalid']}")
    print(f"- entries_ignored_invalid_session: {stats_dict['entries_ignored_invalid_session']}")
    print(f"- sum_valid_values: {stats_dict['sum_valid_values']}")
    print("")

    print("Invalid session reasons")
    print(stats_dict["invalid_session_reasons"] or "{}")
    print("")

    print("Invalid entry reasons")
    print(stats_dict["invalid_entry_reasons"] or "{}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    strict_entry_keys = not args.no_strict_entry_keys
    stats = process_quarterly(
        args.sessions_root,
        strict_entry_keys=strict_entry_keys,
    )
    stats_dict = asdict(stats)

    if args.json:
        print(json.dumps(stats_dict, indent=2, sort_keys=True))
        return

    _print_human(stats_dict, args.sessions_root, strict_entry_keys)


if __name__ == "__main__":
    main()
