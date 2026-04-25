# Tricura - Approach

This project was developed with a layered, evidence-first approach. The goal was not only to compute the quarterly metric, but also to keep implementation and investigation steps reviewable. Layers were added in an order that reduces coupling and improves traceability during normal execution.

## Architecture and implementation strategy

The first step was defining domain models for sessions and entries. This created a stable contract between raw JSON and business logic. With those contracts in place, reference data was centralized as immutable configuration (departments, processors, bins, categories, and valid time window), preventing hidden constants and keeping rule inputs explicit.

Validation came next with two levels: session and entry. The split is intentional: session failures invalidate the full document, while entry failures are localized. Validation returns structured reasons used for both metrics and anomaly triage.

After rule logic was stable, filesystem access was isolated in a repository layer. That module only discovers files and parses JSON into domain objects, with no business-rule knowledge. Error handling was hardened to surface parse/read issues with clear messages.

Finally, orchestration was implemented in a service layer as one deterministic pipeline: list files, load sessions, validate sessions, validate entries, aggregate totals, and report rejection histograms.

## Operational observability in the main flow

A key requirement was to discover anomalies naturally, without side scripts or feature toggles, so observability was integrated directly into the main processing flow.

The pipeline now logs:
- start/end of execution;
- periodic progress checkpoints;
- rejected sessions with reason and file context;
- unexpected entry fields with session id, file path, and entry ref;
- rare anomaly candidates from final reason histograms.

This enables scan-and-investigate behavior during ordinary runs. Instead of assuming hidden clues, the system surfaces low-frequency signals and points to source artifacts.

## Investigation method and natural discovery trail

The investigation flow is strict and evidence-driven:
1. run processing normally;
2. inspect aggregate reasons and warnings;
3. prioritize rare anomalies;
4. open the exact referenced file;
5. inspect raw payload and related portal artifacts;
6. continue only when each step yields reproducible evidence.

Using this method, one unexpected-field warning became the pivot for deeper analysis. The field value led to a route. The route page required source-level inspection (not just rendered content). Source comments revealed the next internal path. The `heritage.html` page provided `word.char` coordinates, and the text-base ("book") was the Founder’s Creed from the portal home page. Applying coordinates to that Creed produced `coldharbor`, which mapped to `/cold-harbor.html`. Accessing that endpoint returned "Designation Confirmed", validating the investigation trail end to end. Each transition was backed by observable artifacts, not prior assumptions.

## Why this approach is robust

This workflow combines clean architecture with investigative rigor. Layering keeps the code maintainable, and in-flow observability turns routine runs into guided analysis. The final outcome is not only a computed sum, but also a defensible chain of evidence that another reviewer can replay end to end.
