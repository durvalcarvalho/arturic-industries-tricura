"""Processing: load sessions -> dedup -> validate -> aggregate.

This module ties all layers together to run the full processing pipeline:

- Read all .mdr files under the sessions directory
- Parse them into SessionDocument
- Deduplicate by session_id, keeping first by timestamp (rule 11)
- Validate sessions (rules 1, 2, 6, 7, 12)
- Validate entries (rules 3, 4, 5, 8-9, 10)
- Sum valid values and collect rejection statistics
"""

import logging
from pathlib import Path

from .models import EntryRecord, SessionDocument
from .reference import ReferenceData, default_reference
from .repository import iter_session_files, load_session
from .validation import ALLOWED_ENTRY_KEYS, RunStats, validate_entry, validate_session

logger = logging.getLogger(__name__)

# Log progress every 25 files
_PROGRESS_EVERY_FILES = 25

# Log rare reasons if the count is less than or equal to 3
_RARE_REASON_THRESHOLD = 3


def process_quarterly(
    sessions_root: Path,
    *,
    reference: ReferenceData | None = None,
    strict_entry_keys: bool = True,
) -> RunStats:
    """Run the processing pipeline applying rules 1-12."""
    ref = reference or default_reference()
    all_paths = _session_paths(sessions_root)

    all_docs = [load_session(path) for path in all_paths]
    unique_docs = _dedup_sessions(all_docs)

    stats = RunStats()
    stats.files_seen = len(all_paths)
    stats.files_used = len(unique_docs)
    logger.info(
        "Starting quarterly processing: root=%s files=%d after_dedup=%d",
        sessions_root,
        stats.files_seen,
        stats.files_used,
    )

    for index, doc in enumerate(unique_docs, start=1):
        _process_session(doc, stats, ref, strict_entry_keys=strict_entry_keys)
        _log_progress(index, stats.files_used, stats)

    logger.info(
        "Finished quarterly processing: files=%d after_dedup=%d sessions_valid=%d "
        "sessions_invalid=%d entries_seen=%d entries_valid=%d entries_invalid=%d "
        "sum_valid_values=%.2f",
        stats.files_seen,
        stats.files_used,
        stats.sessions_valid,
        stats.sessions_invalid,
        stats.entries_seen,
        stats.entries_valid,
        stats.entries_invalid,
        stats.sum_valid_values,
    )
    logger.info("Invalid session reasons: %s", stats.invalid_session_reasons)
    logger.info("Invalid entry reasons: %s", stats.invalid_entry_reasons)
    _log_rare_reasons("session", stats.invalid_session_reasons)
    _log_rare_reasons("entry", stats.invalid_entry_reasons)
    return stats


def _session_paths(sessions_root: Path) -> list[Path]:
    return list[Path](iter_session_files(sessions_root))


def _dedup_sessions(docs: list[SessionDocument]) -> list[SessionDocument]:
    """Rule 11: keep only the first occurrence of each session_id by timestamp."""
    seen: dict[str, SessionDocument] = {}
    duplicates_removed = 0

    for doc in docs:
        if doc.session_id not in seen:
            seen[doc.session_id] = doc
        else:
            seen[doc.session_id] = _resolve_duplicate(seen[doc.session_id], doc)
            duplicates_removed += 1

    logger.info("Dedup complete: %d duplicates removed, %d unique sessions", duplicates_removed, len(seen))
    return list(seen.values())


def _resolve_duplicate(existing: SessionDocument, incoming: SessionDocument) -> SessionDocument:
    """Return whichever duplicate has the earlier timestamp, preferring the existing one on ties."""
    from .validation import _parse_session_timestamp

    existing_ts = _parse_session_timestamp(existing.timestamp)
    incoming_ts = _parse_session_timestamp(incoming.timestamp)

    if existing_ts is not None and incoming_ts is not None and incoming_ts < existing_ts:
        logger.info(
            "Dedup: replaced session_id=%s (kept earlier timestamp %s over %s)",
            incoming.session_id,
            incoming_ts,
            existing_ts,
        )
        return incoming

    logger.info(
        "Dedup: discarded duplicate session_id=%s path=%s",
        incoming.session_id,
        incoming.source_path,
    )
    return existing


def _process_session(
    doc: SessionDocument,
    stats: RunStats,
    ref: ReferenceData,
    *,
    strict_entry_keys: bool,
) -> None:
    """Validate a session and, if valid, process its entries."""
    sv = validate_session(doc, ref)
    if not sv.ok:
        _record_invalid_session(doc, stats, sv.reasons)
        return

    stats.sessions_valid += 1
    invalid_before = stats.entries_invalid
    for entry in doc.entries:
        _process_entry(doc, entry, stats, ref, strict_entry_keys=strict_entry_keys)
    _log_rejected_entries(doc, stats.entries_invalid - invalid_before, len(doc.entries))


def _record_invalid_session(
    doc: SessionDocument, stats: RunStats, reasons: set[str]
) -> None:
    """Update stats and log for a rejected session."""
    stats.sessions_invalid += 1
    stats.bump_reason(stats.invalid_session_reasons, reasons)
    stats.entries_ignored_invalid_session += len(doc.entries)
    logger.warning(
        "Rejected session: id=%s path=%s reasons=%s ignored_entries=%d",
        doc.session_id,
        doc.source_path,
        list(reasons),
        len(doc.entries),
    )


def _log_rejected_entries(doc: SessionDocument, invalid_count: int, total: int) -> None:
    if invalid_count > 0:
        logger.debug(
            "Session had rejected entries: id=%s path=%s invalid_entries=%d total_entries=%d",
            doc.session_id,
            doc.source_path,
            invalid_count,
            total,
        )


def _process_entry(
    doc: SessionDocument,
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
    ev = validate_entry(entry, ref, department=doc.department, strict_keys=strict_entry_keys)
    if not ev.ok:
        stats.entries_invalid += 1
        stats.bump_reason(stats.invalid_entry_reasons, ev.reasons)
        extra_keys = sorted(set(entry.raw.keys()) - ALLOWED_ENTRY_KEYS)
        if extra_keys:
            logger.warning(
                "Unexpected entry fields: session_id=%s path=%s entry_ref=%s extra_keys=%s",
                doc.session_id,
                doc.source_path,
                entry.ref,
                extra_keys,
            )
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


def _log_rare_reasons(reason_type: str, reason_counts: dict[str, int]) -> None:
    for reason, count in sorted(reason_counts.items(), key=lambda item: (item[1], item[0])):
        if count <= _RARE_REASON_THRESHOLD:
            logger.warning(
                "Rare anomaly candidate: type=%s reason=%s count=%d",
                reason_type,
                reason,
                count,
            )
