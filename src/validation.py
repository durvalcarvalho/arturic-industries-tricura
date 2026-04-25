"""Validation engine: Processing Manual rules 1-6 and Compliance Annex rules 7-12.

Two levels of validation are applied in sequence:

1. Session-level (validate_session): checks department, processor,
   timestamp window (rules 1, 2, 6), processor termination (rule 7),
   and weekday-only policy (rule 12).

2. Entry-level (validate_entry): checks bin, category, value
   (rules 3, 4, 5), department-bin authorization (rules 8-9),
   and value ceiling (rule 10).

Rule 11 (duplicate session dedup) is handled in the service layer
before validation, since it requires cross-session awareness.
"""

import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any

from .models import EntryRecord, SessionDocument
from .reference import ReferenceData

logger = logging.getLogger(__name__)

_SESSION_TS_FORMATS: tuple[str, ...] = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f")

# The Manual documents exactly these four keys for each entry row.
ALLOWED_ENTRY_KEYS: frozenset[str] = frozenset({"ref", "bin", "value", "category"})


def _parse_session_timestamp(value: object) -> datetime | None:
    """Try known timestamp formats and return None if all fail.

    It tries to parse the timestamp in two different formats:
    - %Y-%m-%dT%H:%M:%S -> example: 2025-10-01T00:00:00
    - %Y-%m-%dT%H:%M:%S.%f -> example: 2025-10-01T00:00:00.000000
    """
    if not isinstance(value, str):
        logger.info(
            "Failed to parse timestamp: non-string value %r (type: %s)",
            value,
            type(value).__name__,
        )
        return None

    for fmt in _SESSION_TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)

        except ValueError:
            continue

    logger.info("Failed to parse timestamp: %s", value)
    return None


def _is_real_number(value: Any) -> bool:
    """Accept int/float, but reject bool (bool is a subclass of int in Python).

    Log when value is not int or float, or when it is a bool.
    """
    # First, check if it's int or float at all
    if not isinstance(value, (int, float)):
        logger.info(
            "Value is not a number (int or float): %r (type: %s)",
            value,
            type(value).__name__,
        )
        return False

    # Then, explicitly reject bool (subclass of int)
    if isinstance(value, bool):
        logger.info("Value is a boolean (should not be accepted as a number): %r", value)
        return False

    # Reject non-finite numerics to avoid corrupting aggregates (NaN, inf, -inf).
    numeric = float(value)
    if not math.isfinite(numeric):
        logger.info("Value is non-finite numeric (NaN/inf): %r", value)
        return False

    # Otherwise, it's a valid real number
    return True


def _to_decimal(value: Any) -> Decimal | None:
    """Convert a numeric payload to Decimal, rejecting invalid/non-finite values."""
    if not _is_real_number(value):
        return None

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        logger.info("Value cannot be converted to Decimal: %r", value)
        return None

    if not decimal_value.is_finite():
        logger.info("Decimal value is non-finite (NaN/inf): %r", value)
        return None

    return decimal_value


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
    """Apply Manual rules 1, 2, 6 and Annex rules 7, 12."""
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

    if ts is not None:
        # Rule 7: terminated processors (sessions after termination date are invalid).
        cutoff = ref.terminated_processors.get(doc.processor)
        if cutoff is not None and ts >= cutoff:
            reasons.append("processor_terminated")

        # Rule 12: weekday sessions only (facility closed on weekends).
        if ts.weekday() >= 5:
            reasons.append("weekend_session")

    return SessionValidation(ok=len(reasons) == 0, reasons=tuple(reasons))


def validate_entry(
    entry: EntryRecord,
    ref: ReferenceData,
    *,
    department: str,
    strict_keys: bool = True,
) -> EntryValidation:
    """Apply Manual rules 3, 4, 5 and Annex rules 8-9, 10."""
    reasons: list[str] = []

    if strict_keys:
        extra = set(entry.raw.keys()) - ALLOWED_ENTRY_KEYS
        if extra:
            reasons.append(f"unexpected_fields:{sorted(extra)}")

    # Rule 3: bin must be one of the 4 signals.
    if entry.bin not in ref.bins:
        reasons.append("bin_not_allowed")

    # Rule 4: category must match the allowed, case-sensitive set.
    if entry.category not in ref.categories:
        reasons.append("category_not_allowed")

    # Rule 5: numeric and strictly positive value.
    decimal_value = _to_decimal(entry.value)
    if decimal_value is None:
        reasons.append("value_not_numeric")
    elif decimal_value <= Decimal("0"):
        reasons.append("value_not_positive")
    else:
        # Rule 10: value ceiling (must be strictly less than 1000.00).
        if decimal_value >= Decimal(str(ref.value_ceiling)):
            reasons.append("value_above_ceiling")

    # Rules 8-9: department-bin authorization matrix.
    allowed_bins = ref.department_bin_matrix.get(department)
    if allowed_bins is not None and entry.bin not in allowed_bins:
        reasons.append("department_bin_not_authorized")

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

    sum_valid_values: Decimal = field(default_factory=lambda: Decimal("0.00"))  # Sum of valid values
    invalid_session_reasons: dict[str, int] = field(default_factory=dict)  # Histogram of invalid session reasons

    invalid_entry_reasons: dict[str, int] = field(default_factory=dict)  # Histogram of invalid entry reasons

    def bump_reason(self, bucket: dict[str, int], reasons: tuple[str, ...]) -> None:
        """Increment histogram counters for each rejection reason."""
        for reason in reasons:
            bucket[reason] = bucket.get(reason, 0) + 1
