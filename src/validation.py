"""Validation engine: Processing Manual rules 1 to 6.

Two levels of validation are applied in sequence:

1. Session-level (validate_session): checks department, processor,
   and timestamp in the Q4/2025 window.

2. Entry-level (validate_entry): checks bin, category, and value
   for each row inside a valid session.

TODO: Check if Compliance Annex has more rules. Add them if needed.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import EntryRecord, SessionDocument
from .reference import ReferenceData

logger = logging.getLogger(__name__)

_SESSION_TS_FORMATS: tuple[str, ...] = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")

# The Manual documents exactly these four keys for each entry row.
ALLOWED_ENTRY_KEYS: frozenset[str] = frozenset({"ref", "bin", "value", "category"})


def _parse_session_timestamp(value: str) -> datetime | None:
    """Try known timestamp formats and return None if all fail.

    It tries to parse the timestamp in two different formats:
    - %Y-%m-%dT%H:%M:%S -> example: 2025-10-01T00:00:00
    - %Y-%m-%dT%H:%M:%S.%f -> example: 2025-10-01T00:00:00.000000
    """
    for fmt in _SESSION_TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)

        except ValueError:
            continue

    logger.error(f"Failed to parse timestamp: {value}")
    return None


def _is_real_number(value: Any) -> bool:
    """Accept int/float, but reject bool (bool is a subclass of int in Python).

    Log when value is not int or float, or when it is a bool.
    """
    # First, check if it's int or float at all
    if not isinstance(value, (int, float)):
        logger.error(f"Value is not a number (int or float): {value!r} (type: {type(value).__name__})")
        return False

    # Then, explicitly reject bool (subclass of int)
    if isinstance(value, bool):
        logger.error(f"Value is a boolean (should not be accepted as a number): {value!r}")
        return False

    # Otherwise, it's a valid real number
    return True


@dataclass(slots=True)
class SessionValidation:
    """Outcome of validating a session header."""

    ok: bool
    reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class EntryValidation:
    """Outcome of validating one entry."""

    ok: bool
    reasons: tuple[str, ...] = ()


def validate_session(
    doc: SessionDocument,
    ref: ReferenceData,
) -> SessionValidation:
    """Apply Manual rules 1, 2, and 6."""
    reasons: list[str] = []

    # Rule 1: department must be authorized.
    if doc.department not in ref.departments:
        reasons.append("department_not_allowed")

    # Rule 2: processor must be authorized.
    if doc.processor not in ref.processors:
        reasons.append("processor_not_authorized")

    # Rule 6: timestamp must parse and be in Q4/2025.
    ts = _parse_session_timestamp(doc.timestamp)
    if ts is None:
        reasons.append("timestamp_unparseable")

    elif ts < ref.window_start or ts > ref.window_end:
        reasons.append("timestamp_outside_q4_2025")

    # TODO: May add here later the Compliance Annex rules
    return SessionValidation(ok=len(reasons) == 0, reasons=tuple(reasons))


def validate_entry(
    entry: EntryRecord,
    ref: ReferenceData,
    *,
    strict_keys: bool = True,
) -> EntryValidation:
    """Apply Manual rules 3, 4, and 5."""
    reasons: list[str] = []

    # Check if any unexpected fields are present in the entry. This may lead to some important info
    if strict_keys:
        extra = set(entry.raw.keys()) - ALLOWED_ENTRY_KEYS
        if extra:
            reasons.append(f"unexpected_fields:{sorted(extra)}")

    # Rule 3: bin must be one of the 4 signals
    if entry.bin not in ref.bins:
        reasons.append("bin_not_allowed")

    # Rule 4: category must match the allowed, case-sensitive set
    if entry.category not in ref.categories:
        reasons.append("category_not_allowed")

    # Rule 5: numeric and strictly positive value
    if not _is_real_number(entry.value):
        reasons.append("value_not_numeric")

    elif float(entry.value) <= 0:
        reasons.append("value_not_positive")

    # TODO: May add here later the Compliance Annex rules
    return EntryValidation(
        ok=len(reasons) == 0,
        reasons=tuple(reasons),
    )


@dataclass(slots=True)
class RunStats:
    """Counters collected during a full run."""

    files_seen: int = 0  # Number of files processed
    files_used: int = 0  # Number of files used (excluding duplicates)

    sessions_valid: int = 0  # Number of sessions validated
    sessions_invalid: int = 0  # Number of sessions invalid

    entries_seen: int = 0  # Number of entries processed
    entries_ignored_invalid_session: int = 0  # Number of entries ignored due to invalid session

    entries_valid: int = 0  # Number of entries validated
    entries_invalid: int = 0  # Number of entries invalid

    sum_valid_values: float = 0.0  # Sum of valid values
    invalid_session_reasons: dict[str, int] = field(default_factory=dict)  # Histogram of invalid session reasons

    invalid_entry_reasons: dict[str, int] = field(default_factory=dict)  # Histogram of invalid entry reasons

    def bump_reason(self, bucket: dict[str, int], reasons: tuple[str, ...]) -> None:
        """Increment histogram counters for each rejection reason."""
        for reason in reasons:
            bucket[reason] = bucket.get(reason, 0) + 1
