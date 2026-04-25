#!/usr/bin/env python3
"""Brute-force the Compliance Annex access code.

The Compliance Annex page (compliance.html) verifies the access code
client-side: the input is trimmed, uppercased, then SHA-256 hashed and
compared against a known target hash.  If it matches, a second hash
(code + "arturic") determines the URL of the unlocked page.

This script exhaustively tries all uppercase alphabetic strings from
length 2 to a configurable maximum (default 6).  On the author's
machine the match was found at length 6 in ~70 seconds:

    JANSKY  (Karl Jansky, Bell Labs Holmdel radio astronomer)

Usage:
    python scripts/bruteforce_access_code.py
    python scripts/bruteforce_access_code.py --max-length 7
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import string
import sys
import time

TARGET_HASH = (
    "38b19f2e76c9fa1e3ab74c80fb3e95b3cd761ce39b0e2359b6ac15e012220907"
)
SUFFIX = "arturic"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _generate_candidates(length: int) -> itertools.product[tuple[str, ...]]:
    return itertools.product(string.ascii_uppercase, repeat=length)


def _check_candidate(candidate: str) -> bool:
    return _sha256(candidate) == TARGET_HASH


def _annex_page_url(code: str) -> str:
    return f"{_sha256(code + SUFFIX)}.html"


def _try_length(length: int) -> str | None:
    total = len(string.ascii_uppercase) ** length
    print(f"Trying length {length} ({total:,} candidates)...")

    start = time.time()
    for combo in _generate_candidates(length):
        code = "".join(combo)
        if _check_candidate(code):
            print(f"  MATCH: '{code}'  ({time.time() - start:.1f}s)")
            print(f"  Annex page: {_annex_page_url(code)}")
            return code

    print(f"  No match at length {length} ({time.time() - start:.1f}s)")
    return None


def search(max_length: int = 6) -> str | None:
    for length in range(2, max_length + 1):
        match = _try_length(length)
        if match is not None:
            return match
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Brute-force the Compliance Annex access code."
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=6,
        help="Maximum code length to try (default: 6)",
    )
    args = parser.parse_args()

    result = search(args.max_length)
    if result is None:
        print("No match found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
