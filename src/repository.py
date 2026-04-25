"""Filesystem access layer for quarterly .mdr session files

Responsibilities:
  - Discover all .mdr files under the sessions directory tree.
  - Parse each file into a SessionDocument.

Important: This module intentionally knows nothing about validation rules, it only
handles I/O so that the rest of the codebase stays decoupled from the
filesystem.
"""

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Mapping

from .models import SessionDocument

logger = logging.getLogger(__name__)


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
    payload = _read_session_payload(path)
    return _to_session_document(payload, path)


def _read_session_payload(path: Path) -> Mapping[str, Any]:
    """Read and parse raw JSON payload from a single .mdr file."""
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

    except json.JSONDecodeError as e:
        msg = f"Failed to parse {path}: {e}"
        logger.error(msg)
        raise ValueError(msg) from e

    except UnicodeDecodeError as e:
        msg = f"Failed to read {path}: {e}"
        logger.error(msg)
        raise ValueError(msg) from e

    except Exception as e:
        msg = f"Failed to read {path}: {e}"
        logger.error(msg)
        raise ValueError(msg) from e

    return payload


def _to_session_document(payload: Mapping[str, Any], path: Path) -> SessionDocument:
    """Convert a parsed payload into SessionDocument."""
    return SessionDocument.from_raw(payload, path)
