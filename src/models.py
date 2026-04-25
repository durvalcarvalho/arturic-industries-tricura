"""Domain models for session files and their entries.

Each .mdr file maps to one SessionDocument containing zero or more
EntryRecord rows.

These are plain dataclasses, no validation logic lives here; that belongs in validation.py.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(slots=True)
class EntryRecord:
    ref: str
    bin: str
    category: str
    value: Any

    #: The raw JSON data from the source file.
    raw: Mapping[str, Any] = field(repr=False)

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "EntryRecord":
        """Create an EntryRecord from raw JSON data."""

        return cls(
            ref=raw["ref"],
            bin=raw["bin"],
            category=raw["category"],
            value=raw["value"],
            raw=raw,
        )


@dataclass(slots=True)
class SessionDocument:
    session_id: str
    processor: str
    department: str
    # Raw timestamp string from session JSON; parsing/validation is handled downstream.
    timestamp: str
    entries: list[EntryRecord]

    # The path to the source file
    source_path: Path

    # The raw JSON data from the source file
    raw: Mapping[str, Any] = field(repr=False)

    @classmethod
    def from_raw(
        cls,
        raw: Mapping[str, Any],
        source_path: Path,
    ) -> "SessionDocument":
        """Create a SessionDocument from a full session file."""

        session_id = raw["session_id"]
        processor = raw["processor"]
        department = raw["department"]
        timestamp = raw["timestamp"]
        entries = [EntryRecord.from_raw(entry) for entry in raw["entries"]]

        return cls(
            session_id=session_id,
            processor=processor,
            department=department,
            timestamp=timestamp,
            entries=entries,
            source_path=source_path,
            raw=raw,
        )
