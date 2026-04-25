"""Authoritative reference data from the Arturic Industries Employee Portal.

Sources:
  - Department Directory  (directory.html): departments, processors, bins, categories
  - Processing Manual     (manual.html):    validation rules 1-6 (Q4 2025 window)
  - Compliance Annex      (locked):         ??

These values are treated as immutable configuration: the frozen dataclass
and frozensets prevent accidental mutation at runtime.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReferenceData:
    """Immutable lookup tables for all six validation rules.

    fronzensets is used instead of "set" because this object is immutable. A multable set
    inside a immutable object would be a recipe for disaster. A frozenset prevents
    accidental mutation, and makes the intent clear: reference data does not change after
    construction.
    """

    departments: frozenset[str]
    processors: frozenset[str]
    bins: frozenset[str]
    categories: frozenset[str]
    window_start: datetime
    window_end: datetime


def default_reference() -> ReferenceData:
    """Build the canonical reference from the Employee Portal (as of Q4 2025)."""
    return ReferenceData(
        departments=frozenset[str]({"MDR", "SA", "WB"}),
        processors=frozenset[str](
            {
                "James.L",
                "Nora.K",
                "Arthur.B",
                "Lena.P",
                "Felix.G",
                "Dr.Voss",
                "Clara.M",
            }
        ),
        bins=frozenset[str]({"GR", "BL", "AX", "SP"}),
        categories=frozenset[str]({"alpha", "beta", "gamma", "delta"}),
        window_start=datetime(2025, 10, 1, 0, 0, 0),
        window_end=datetime(2025, 12, 31, 23, 59, 59),
    )
