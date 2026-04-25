"""Decode suspicious extra-field values from session entries.

Usage:
  python3 decode_clue.py quarterly_output/sessions/MDR/MDR-0156.mdr --field calibration_note
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Any

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode suspicious entry field values from a .mdr file.",
    )
    parser.add_argument(
        "session_file",
        type=Path,
        help="Path to the .mdr session file.",
    )
    parser.add_argument(
        "--field",
        default="calibration_note",
        help="Suspicious field name to inspect (default: calibration_note).",
    )
    parser.add_argument(
        "--entry-ref",
        default=None,
        help="Optional entry ref filter (example: GR-X042).",
    )
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_base64_candidate(value: str) -> bool:
    token = value.strip()
    return len(token) >= 16 and len(token) % 4 == 0 and _BASE64_RE.fullmatch(token) is not None


def _try_base64_decode(value: str) -> str | None:
    if not _is_base64_candidate(value):
        return None
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except Exception:
        return None
    return decoded


def main() -> None:
    args = _build_parser().parse_args()
    data = _load_json(args.session_file)
    entries = data.get("entries", [])

    matches = []
    for entry in entries:
        if args.entry_ref is not None and entry.get("ref") != args.entry_ref:
            continue
        if args.field in entry:
            matches.append(entry)

    if not matches:
        print(f"No entry found with field={args.field!r} in {args.session_file}")
        return

    print(f"Found {len(matches)} entry(s) with field={args.field!r}")
    for idx, entry in enumerate(matches, start=1):
        raw_value = entry.get(args.field)
        print(f"\n[{idx}] entry_ref={entry.get('ref')}")
        print(f"raw: {raw_value!r}")

        if not isinstance(raw_value, str):
            print("decoded: skipped (value is not text)")
            continue

        decoded = _try_base64_decode(raw_value)
        if decoded is None:
            print("decoded: no supported decoding succeeded")
            continue

        print("decoded (base64):")
        print(decoded)


if __name__ == "__main__":
    main()
