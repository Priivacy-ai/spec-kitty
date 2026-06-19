# Phase 0 Research: Untrusted-Path Containment Hardening

## Decision 1 — Close the store.py symlink-dir residual now (Q1→A)

- **Decision**: Add `resolve()`-containment to `status/store.py._SlugResolver.resolve`, reusing `core/utils.py.ensure_within_any`. Keep the existing `assert_safe_path_segment` grammar check as the first gate.
- **Rationale**: The segment-grammar guard rejects `..`/separators/absolute paths, but `store.py` then does `.exists()`/`read_text()` with no `resolve()`-containment, so a *valid single label* that is a **symlink directory** under `kitty-specs/` pointing outside still escapes (witnessed in the squad review). `ensure_within_any` resolves symlinks (`resolve(strict=False)`) and checks containment — the same mechanism merge.py already uses.
- **Aggregate scope correction (review, code-verified)**: there is NO `_SlugResolver` analog in `aggregate.py`. Its slug guard `_validate_mission_slug` (aggregate.py:344-359) already calls `assert_safe_path_segment` and **raises** `InvalidMissionSlug` (callers catch it). So FR-003 is not resolver-parity work; it is documenting that raise-guard and handing aggregate's composed-path reads (`_find_meta_path` glob) to the IC-02 audit for a containment disposition.
- **Alternatives considered**: (a) accept as documented residual — rejected: the mission's point is closing the *class*, and the bar (write access in specs dir) is plausible in shared checkouts; (b) lstat/no-follow — rejected: `resolve()`-containment is the canonical approach already in the tree.

## Decision 6 — macOS symlinked-root containment (avoid false rejects)

- **Decision**: Compute containment resolved-to-resolved: callers pass the **un-resolved logical root** to `ensure_within_any`, which resolves both sides. Test fixtures MUST include a symlinked-root **positive** case proving a legitimate slug under a symlinked root is ACCEPTED, in addition to the symlink-escape negative case.
- **Rationale**: `ensure_within_any` resolves both candidate and roots with `resolve(strict=False)`. On macOS/CI, `tmp_path` is commonly under `/var`→`/private/var` or `/tmp`→`/private/tmp`. A naive test that resolves only one side, or a guard wired to a pre-resolved root, would FALSE-REJECT a legitimate slug on macOS (NFR-003 regression) while passing on Linux. This is the standard `/var`→`/private/var` trap.
- **TOCTOU**: out of scope (threat model: on-disk state authored before the run, not concurrently mutated).

## Decision 7 — meta.json slug bypass of the reducer seam (Blocker, code-verified) → IC-05

- **Finding**: PR #2036's reducer-seam chokepoint sanitizes only the event-log slug. `views.py:_stale_check_slug`→`resolve_mission_identity` (mission_metadata.py:225) and the `lifecycle.py:340-341` empty-slug fallback read `meta.json mission_slug` UNVALIDATED and join it into `derived_dir / <slug>` + `mkdir`. A hostile event slug downgraded to `""` by the reducer actively triggers this fallback — so the write-path traversal is still live. `progress.py` is unaffected (uses only `snapshot.mission_slug or feature_dir.name`).
- **Decision**: Route `resolve_mission_identity().mission_slug` through `safe_mission_slug(..., feature_dir.name)` at the single source (`mission_metadata.py:225`), covering both consumers. Captured as IC-05 / FR-009.
- **Note**: this is a still-open vulnerability on the #2036 branch; closing it is now in-scope for this mission rather than a #2036 follow-on.

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
