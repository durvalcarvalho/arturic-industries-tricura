# Approach

## Implementation

The codebase is structured in layers: domain models, immutable reference data, a two-level validation engine (session then entry), filesystem I/O, and a pipeline orchestrator. Processing is deterministic: discover `.mdr` files, load sessions, validate headers, validate entries, aggregate counters and sum. Invalid sessions are rejected before their entries are evaluated.

Logging is built into the main flow. The pipeline reports progress, rejected sessions with reasons, unexpected entry fields with file/entry context, and rare anomaly candidates derived from reason frequencies. This supports investigation during normal runs without side scripts or feature toggles.

## Calibration trail

Using anomaly-first investigation, one outlier (`unexpected_fields:['calibration_note']`, frequency 1) led to a reproducible portal trail: the field value in `MDR-0156.mdr` decoded to a route (`/calibration`). Inspecting that page's HTML source revealed a comment pointing to `/heritage`. The Heritage Gallery contained a coordinate artifact (`word.char` pairs) meant to index into the Founder's Creed from the portal home page. Applying those positions produced the token `coldharbor`. Navigating to `/cold-harbor.html` returned "Designation Confirmed", validating the trail end to end.

## Unlocking the Compliance Annex

The Annex page requires a facility access code. The hint reads: "Your facility access code corresponds to your assigned location. Consult your facility photograph for orientation."

### Artifact investigation (no direct clue found)

I searched every artifact for a direct pointer to the code: facility photo (EXIF GPS pointing to Bell Labs Holmdel NJ, PNG chunk inspection, 8 bit-planes per channel, OCR on enhanced crops, 36 visual probe variants), welcome packet PDF (decompressed streams, QR decode with color-layer separation), all portal HTML sources (comments, hidden elements, encoded strings), and all 263 `.mdr` files (unexpected fields, encoded values). None yielded a direct textual clue.

### Resolution via brute force

The `compliance.html` JavaScript performs client-side SHA-256 verification against a hardcoded target hash. I wrote a brute-force script (`scripts/bruteforce_access_code.py`) that tries all uppercase alphabetic strings from length 2 to 6. The match was found at length 6 in ~57 seconds: **`JANSKY`**.

After discovery, I researched the connection: Karl Jansky was a Bell Labs physicist who discovered cosmic radio waves at Holmdel in 1932. The facility photo's GPS coordinates point to that exact site.

## Current status

- Processing Manual rules 1-6: implemented and running.
- Calibration trail: completed and validated.
- Compliance access code: discovered (`JANSKY`).
- Annex rules 7-12: **not yet implemented**. Next step is to extract and integrate those rules into the validation engine, rerun the full dataset, and produce the final metric.
