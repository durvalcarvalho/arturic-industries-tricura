# Tricura - Approach

The implementation followed a simple order so reviewers can understand intent quickly: define the data shape, define the rules, isolate I/O, then orchestrate everything in one pipeline.

## Thinking flow

1. **Model first, logic later**  
   Start with explicit domain models for session documents and entries. This gives a stable contract for every next layer and avoids validation logic tied to raw JSON.

2. **Centralize reference truth**  
   Create one reference source for accepted processors, departments, bins, and categories. Validation depends on this source instead of hardcoded values spread across files.

3. **Implement validation in isolation**  
   Build session-level and entry-level checks as a dedicated validation layer, including reason tracking for rejected data. This keeps business rules independent from filesystem concerns.

4. **Keep repository focused on I/O**  
   Add a repository layer responsible only for discovering `.mdr` files and loading/parsing them into domain objects. No business rules here.

5. **Harden ingestion path**  
   Add explicit error handling and logging for malformed JSON or unreadable files so failures are visible and diagnosable without crashing silently.

6. **Compose the pipeline**  
   Build a service that orchestrates: file discovery -> load -> session validation -> entry validation -> aggregation of totals and rejection stats.

7. **Refine for readability**  
   After behavior was stable, refactor long functions into smaller focused methods and keep public entry points first in each module. This improves reviewability and future maintenance without changing behavior.

## Why this order

This sequence reduces coupling and rework: contracts come first, rules stay isolated, I/O stays isolated, and orchestration becomes straightforward. It also makes testing easier because each layer has one responsibility.
