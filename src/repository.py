"""Filesystem access layer for quarterly .mdr session files

Responsibilities:
  - Discover all .mdr files under the sessions directory tree.
  - Parse each file into a SessionDocument.

Important: This module intentionally knows nothing about validation rules, it only
handles I/O so that the rest of the codebase stays decoupled from the
filesystem.
"""

import json
from collections.abc import Iterator
from pathlib import Path

from .models import SessionDocument


def iter_session_files(sessions_root: Path) -> Iterator[Path]:
    """Yield every .mdr file under *sessions_root*, sorted by path.

    Returns a generator (yield from) so files are produced
    lazily (no need to load all files at once). It's useful if the dataset ever grows
    large enough that building a full list up-front becomes wasteful.
    """
    if not sessions_root.is_dir():
        raise FileNotFoundError(sessions_root)

    yield from sorted(sessions_root.rglob("*.mdr"))


def load_session(path: Path) -> SessionDocument:
    """Read and parse a single .mdr JSON file into a domain object."""
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    return SessionDocument.from_raw(payload, path)
