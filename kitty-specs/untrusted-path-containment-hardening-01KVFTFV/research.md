# Phase 0 Research: Untrusted-Path Containment Hardening

## Decision 1 — Close the store.py symlink-dir residual now (Q1→A)

- **Decision**: Add `resolve()`-containment to `status/store.py._SlugResolver.resolve` and to the sibling `status/aggregate.py` resolver, reusing `core/utils.py.ensure_within_any`. Keep the existing `assert_safe_path_segment` grammar check as the first gate.
- **Rationale**: The segment-grammar guard rejects `..`/separators/absolute paths, but `store.py` then does `.exists()`/`read_text()` with no `resolve()`-containment, so a *valid single label* that happens to be a **symlink directory** under `kitty-specs/` pointing outside still escapes (witnessed in the squad review). `ensure_within_any` resolves symlinks (`resolve(strict=False)`) and checks containment — the same mechanism merge.py already uses successfully. Fixing both resolvers keeps the two sibling code paths at parity (no third mechanism).
- **Alternatives considered**: (a) accept as documented residual (matches aggregate precedent) — rejected: the mission's whole point is closing the *class*, and the bar (write access in specs dir) is plausible in shared checkouts; (b) lstat/no-follow checks — rejected: `resolve()`-containment is the established canonical approach already in the tree.

## Decision 2 — Full CLI audit, fix reachable, document the rest (Q2→C)

- **Decision**: Enumerate every untrusted-string→FS-path sink in `src/specify_cli`; route confirmed-reachable sinks through the canonical seam; record a disposition for every sink (fixed / not-reachable-documented).
- **Rationale**: Point fixes leave siblings open (already proven: store.py + three write sinks were missed by the original PR). A full audit with a recorded disposition (SC-003) is the only way to claim the class is closed without over-fixing unreachable code.
- **Methodology**: grep for FS sinks (`open`, `read_text`/`read_bytes`, `write_text`/`write_bytes`, `mkdir`, `shutil.copy/move/rmtree`, `unlink`, `Path(...) /` joins) whose path is built from a slug/id sourced from event content, `meta.json`, frontmatter, config, or CLI args. Classify source as trusted (`feature_dir.name`, resolved-identity slug) vs untrusted. For untrusted sinks: route through `assert_safe_path_segment`/`safe_mission_slug` (segment) and/or `ensure_within_any` (containment). The audit record lists each sink with source, sink, reachability, and disposition.
- **Alternatives considered**: status+merge only (too narrow — leaves the class half-open); fix everything blindly (over-fix, churn on unreachable code). Option C balances both.

## Decision 3 — Fail-closed semantics per sink type (C-004)

- **Decision**: Read sinks fail closed by skipping (return `None`); write sinks fail closed by falling back to the trusted `feature_dir.name`; both log exactly one WARNING; neither raises on the hot path.
- **Rationale**: Matches the landed #2036 behaviour (reducer seam already downgrades a hostile slug to `""` → write sinks use their existing `or feature_dir.name` fallback). Consistency across surfaces; no crash, no silent widening (NFR-004).

## Decision 4 — loopback_http.py: document, do not force HTTPS (FR-006, C-001)

- **Decision**: Add an in-code rationale comment explaining the 127.0.0.1-only binding, retain the binding regression tests, and record the two Sonar hotspots for UI review. No behavioural change.
- **Rationale**: Repo policy (and charter "Loopback/local-only HTTP special case") explicitly forbids forcing HTTPS on loopback control-plane URLs. The correct action is rationale + regression lock + hotspot review, not a code change.

## Decision 5 — Regression guard scope (FR-005)

- **Decision**: A `tests/architectural/` test anchored on the IC-02 audited-surface inventory that fails if an untrusted segment is joined to a path without passing the canonical seam on those surfaces.
- **Rationale**: Prevents class regression. Anchoring on the known untrusted sources/sinks (not every `Path /`) keeps false positives low.

## Baseline recognition (FR-007)

PR #2036 is the landed first increment and must not regress: merge bookkeeping
capture-time validation, wrapper `0755→0700`, store.py segment guard,
`safe_mission_slug`, reducer-seam chokepoint. All forward work builds on it.

## Known pre-existing note (Pre-existing Failure Reporting)

`tests/status/test_store.py` has a config-suppressed mypy `os` attr-defined
finding from a #946-era `monkeypatch.setattr(status_store.os, ...)` idiom. It is
invisible to the standard gate (`follow_imports=skip`) and is out of scope; left
as-is to avoid changing an unrelated atomic-write test's patch semantics.
