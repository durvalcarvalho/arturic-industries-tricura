"""Authoritative reference data from the Arturic Industries Employee Portal.

Sources:
  - Department Directory  (directory.html): departments, processors, bins, categories
  - Processing Manual     (manual.html):    validation rules 1-6 (Q4 2025 window)
  - Compliance Annex      (JANSKY):         rules 7-12

These values are treated as immutable configuration: the frozen dataclass
and frozensets prevent accidental mutation at runtime.
"""

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ReferenceData:
    """Immutable lookup tables for all twelve validation rules.

    frozensets are used instead of "set" because this object is immutable.
    A mutable set inside an immutable object would allow silent mutation.
    frozenset prevents that and makes the intent clear: reference data does
    not change after construction.
    """

    departments: frozenset[str]
    processors: frozenset[str]
    bins: frozenset[str]
    categories: frozenset[str]
    window_start: datetime
    window_end: datetime

    # Rule 7: processor termination cutoffs (processor -> last valid datetime)
    terminated_processors: MappingProxyType[str, datetime]

    # Rule 8-9: department -> authorized bins matrix
    department_bin_matrix: MappingProxyType[str, frozenset[str]]

    # Rule 10: value ceiling (exclusive upper bound)
    value_ceiling: float


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
        terminated_processors=MappingProxyType(
            {
                "Nora.K": datetime(2025, 11, 15, 0, 0, 0),
            }
        ),
        department_bin_matrix=MappingProxyType(
            {
                "MDR": frozenset({"GR", "BL", "AX"}),
                "SA": frozenset({"SP", "BL"}),
                "WB": frozenset({"GR", "AX"}),
            }
        ),
        value_ceiling=1000.0,
    )
