"""Processing: load sessions -> validate -> aggregate.

This module glue all the other modules together to perform the processing pipeline.

- Read all .mdr files under the sessions directory
- Parse them into SessionDocument
- Validate sessions (rules 1, 2, 6 via validate_session)
- Validate entries (rules 3, 4, 5 via validate_entry)
- Sum valid values and collect rejection statistics

TODO: Check if Compliance Annex rules has more rules, it may impact here
"""

import logging
from pathlib import Path

from .models import EntryRecord, SessionDocument
from .reference import ReferenceData, default_reference
from .repository import iter_session_files, load_session
from .validation import RunStats, validate_entry, validate_session

logger = logging.getLogger(__name__)

# Log progress every 25 files
_PROGRESS_EVERY_FILES = 25


def process_quarterly(
    sessions_root: Path,
    *,
    reference: ReferenceData | None = None,
    strict_entry_keys: bool = True,
) -> RunStats:
    """Run the processing pipeline applying rules 1-6."""
    # Get the reference data rules
    ref = reference or default_reference()

    # Get the session paths
    all_paths = _session_paths(sessions_root)

    # Initialize the stats aggregator
    stats = _init_run_stats(all_paths)
    logger.info(
        "Starting quarterly processing: root=%s files=%d strict_entry_keys=%s",
        sessions_root,
        stats.files_seen,
        strict_entry_keys,
    )

    # Process each session
    for index, path in enumerate(all_paths, start=1):
        doc = load_session(path)
        _process_session(doc, stats, ref, strict_entry_keys=strict_entry_keys)
        _log_progress(index, stats.files_seen, stats)

    # TODO(annex): may add new stats here after compliance annex rules
    logger.info(
        "Finished quarterly processing: files=%d sessions_valid=%d sessions_invalid=%d "
        "entries_seen=%d entries_valid=%d entries_invalid=%d sum_valid_values=%.2f",
        stats.files_seen,
        stats.sessions_valid,
        stats.sessions_invalid,
        stats.entries_seen,
        stats.entries_valid,
        stats.entries_invalid,
        stats.sum_valid_values,
    )
    logger.info("Invalid session reasons: %s", stats.invalid_session_reasons)
    logger.info("Invalid entry reasons: %s", stats.invalid_entry_reasons)
    return stats


def _session_paths(sessions_root: Path) -> list[Path]:
    return list[Path](iter_session_files(sessions_root))


def _init_run_stats(all_paths: list[Path]) -> RunStats:
    stats = RunStats()
    stats.files_seen = len(all_paths)
    stats.files_used = len(all_paths)
    return stats


def _process_session(
    doc: SessionDocument,
    stats: RunStats,
    ref: ReferenceData,
    *,
    strict_entry_keys: bool,
) -> None:
    """Process a single session.

    Handle the stats aggregation for the session.
      - If the session is invalid, increment the invalid session counter and
      - If the session is valid, process the entries.
    """
    # Validate the session
    sv = validate_session(doc, ref)
    if not sv.ok:
        stats.sessions_invalid += 1
        stats.bump_reason(stats.invalid_session_reasons, sv.reasons)
        stats.entries_ignored_invalid_session += len(doc.entries)
        logger.warning(
            "Rejected session: id=%s path=%s reasons=%s ignored_entries=%d",
            doc.session_id,
            doc.source_path,
            list(sv.reasons),
            len(doc.entries),
        )
        return

    stats.sessions_valid += 1
    invalid_entries_before = stats.entries_invalid
    _process_valid_session_entries(
        doc,
        stats,
        ref,
        strict_entry_keys=strict_entry_keys,
    )
    invalid_entries_in_session = stats.entries_invalid - invalid_entries_before
    if invalid_entries_in_session > 0:
        logger.info(
            "Session processed with rejected entries: id=%s path=%s invalid_entries=%d total_entries=%d",
            doc.session_id,
            doc.source_path,
            invalid_entries_in_session,
            len(doc.entries),
        )


def _process_valid_session_entries(
    doc: SessionDocument,
    stats: RunStats,
    ref: ReferenceData,
    *,
    strict_entry_keys: bool,
) -> None:
    """Process the entries of a valid session."""
    for entry in doc.entries:
        _process_entry(
            entry,
            stats,
            ref,
            strict_entry_keys=strict_entry_keys,
        )


def _process_entry(
    entry: EntryRecord,
    stats: RunStats,
    ref: ReferenceData,
    *,
    strict_entry_keys: bool,
) -> None:
    """Process a single entry.

    Handle the stats aggregation for the entry.
      - If the entry is invalid, increment the invalid entry counter and
      - If the entry is valid, increment the valid entry counter and add the value to the sum of valid values.
    """
    stats.entries_seen += 1

    # Validate the entry
    ev = validate_entry(entry, ref, strict_keys=strict_entry_keys)
    if not ev.ok:
        stats.entries_invalid += 1
        stats.bump_reason(stats.invalid_entry_reasons, ev.reasons)
        return

    stats.entries_valid += 1
    stats.sum_valid_values += float(entry.value)


def _log_progress(processed_files: int, total_files: int, stats: RunStats) -> None:
    if processed_files == total_files or processed_files % _PROGRESS_EVERY_FILES == 0:
        logger.info(
            "Progress: files=%d/%d sessions_valid=%d sessions_invalid=%d entries_seen=%d",
            processed_files,
            total_files,
            stats.sessions_valid,
            stats.sessions_invalid,
            stats.entries_seen,
        )
