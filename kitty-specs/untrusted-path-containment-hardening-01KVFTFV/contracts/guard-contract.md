# Behavioural Contract: Untrusted-Segment Containment Seam

This mission has no network/API surface. The "contracts" are the behavioural
guarantees of the canonical seam at each sink. Each is a testable assertion.

## C-GUARD-1 — segment grammar (assert_safe_path_segment)

- **Input**: a string segment.
- **Accept**: non-empty pure-ASCII label, no separators, not `.`/`..`, not absolute.
- **Reject** (`ValueError`): empty, whitespace, non-ASCII, contains `/` or `\`, `.`/`..`, leading-dot traversal forms, absolute path.

## C-GUARD-2 — fail-closed slug (safe_mission_slug)

- **Input**: `(slug | None, fallback)`.
- **Output**: `slug` when it passes C-GUARD-1; otherwise `fallback` (trusted), plus one WARNING.
- **Never raises.**

## C-GUARD-3 — containment (ensure_within_any)

- **Input**: a built path + the trusted-root set.
- **Behaviour**: `resolve(strict=False)` (follows symlinks), then assert the resolved path is within at least one trusted root.
- **Reject** (`ValueError`): a path that resolves outside all trusted roots — including a symlink whose target escapes.
- **Accept**: a path (or symlink) that resolves to a location inside a trusted root.

## C-SINK-READ — resolver read sinks (store.py, aggregate.py)

- **Given** an untrusted slug, **when** resolving identity from `<root>/<slug>/meta.json`,
- **then** the slug passes C-GUARD-1 and the resolved meta path passes C-GUARD-3 before any `read_text`;
- **on failure**: return `None` (skip the record), emit one WARNING, read nothing outside the root.

## C-SINK-WRITE — derived-view write sinks (progress/lifecycle/views)

- **Given** an untrusted slug from EITHER source — `snapshot.mission_slug` (event log) OR the `meta.json` slug via `resolve_mission_identity` — **when** building `derived_dir/<slug>`,
- **then** BOTH sources are sanitized: the reduce seam (C-GUARD-2) for the event slug (landed #2036) AND `mission_metadata.resolve_mission_identity` (C-GUARD-2, IC-05) for the `meta.json` slug, so an unsafe slug becomes the trusted `feature_dir.name`;
- **result**: no `mkdir`/write outside `derived/`; output lands under `feature_dir.name`.
- **Regression note**: `progress.py` was already safe post-#2036; `views.py`/`lifecycle.py` were NOT (the `meta.json` fallback bypassed the reduce seam) — IC-05 closes them. The negative test MUST cover the `meta.json`-slug + empty-event-slug combination.

## C-REGRESSION — architectural guard

- A new untrusted-segment join on an audited surface that bypasses the seam **fails** the `tests/architectural/` guard.

## Verification

Every contract above is covered by a mutation-killing test: removing the guard
makes at least one test fail (SC-004). The symlink-escape case is explicit for
C-GUARD-3 / C-SINK-READ.
