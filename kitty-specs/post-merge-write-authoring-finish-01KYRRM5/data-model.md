# Data Model — Post-Consolidation Write Surface and Authoring Finish

Phase 1. Entities/value objects, invariants, and state transitions. No new persistence schema (C-008: `NegativeInvariant` fields already exist; no new `merge_target_branch` field, D1).

## LifecyclePhase (derived, not stored)

Computed inside `resolve_placement_only` from durable `meta.json` + git state.

| Phase | Signal | CONSOLIDATED resolves to |
|-------|--------|--------------------------|
| `PRE_CONSOLIDATION` | `baseline_merge_commit` absent | n/a — routing unchanged from #3076 |
| `CONSOLIDATED` (E1) | `baseline_merge_commit` present AND Target Ref branch exists | Target Ref tree |
| `PUBLISHED` (E2) | `baseline_merge_commit` present AND Target Ref absent AND terminal-completion (all WPs `done` / `mission_number` set) | repository-root checkout, gated by content-presence (D1) |

**Invariants**:
- The probe (`write_target`) and materializer (`commit_for_mission`) derive the **identical** phase from the same durable source (NFR-001, no split-brain).
- `PRE_CONSOLIDATION` is the safe default — a legacy null-baseline mission whose Target Ref was never created resolves here, not E2 (C-003).

## SurfaceLocations.consolidated (value)

Existing dataclass field (`resolution.py:1508`, currently always `None`). This mission populates it.

- **Populated** with the integrated-tree path per phase (E1 Target Ref tree; E2 repo-root checkout).
- `translate_surface(CONSOLIDATED, locations)` returns it; raises the existing "caller must supply the location" `ValueError` when `None` (unchanged guard — now reached only in genuinely-unroutable states → FR-006 refuse-with-recovery).

## CONSOLIDATED content-presence predicate (D1)

- **Input**: `mission_slug`, current `HEAD`.
- **Check**: the mission's committed artifact tree is present at `HEAD` (`git cat-file -e HEAD:kitty-specs/<mission_slug>/meta.json` or an equivalent committed marker).
- **Squash-robust**: true regardless of commit topology; does NOT use commit ancestry.
- **On false** in a consolidated/published phase → refuse-with-recovery (FR-006).

## WriteSeamResult (value — extended behaviour, not shape)

`coordination/write_seam.py`. Existing `committed` / `refused` result.

- **New**: a *refused* result leaves **zero** staging residue — the staging thunk (below) is invoked only after `_probe_write_target` passes (FR-005/#3073).
- Refusal remains structured + recoverable (names the recovery action).

## Staging thunk (new seam contract)

`write_artifact(kind, stage: Callable[[], tuple[Path, ...]], …)`.

- `stage` is invoked **only after** the routability probe returns OK, immediately before `commit_for_mission`.
- The three composed writers (`tasks/issue_matrix.py`, `retrospective/tracer_writer.py`, `acceptance/matrix.py`) pass their `write_text`/`write_acceptance_matrix` as the thunk instead of executing it up front.
- `write_acceptance_matrix` stays a standalone function (its no-commit/fixture callers are unaffected — the thunk merely wraps it).

## NegativeInvariant (existing dataclass — no schema change)

`acceptance/matrix.py:107-146`. Already carries all fields (C-008).

- **Register (FR-007)**: `agent mission acceptance-verdict` persists a well-shaped `NegativeInvariant` — zero hand-edited JSON.
- **Execute (FR-008)**: run via the existing `enforce_negative_invariants` engine (`matrix.py:513`); record `result`.
- **Diagnose (FR-009)**: a malformed invariant is reported per-invariant at load, not raised.
- **overall_verdict (FR-010)**: a computed property; canonical acceptance persists the recomputed value (fresh `pass` for all-pass/no-invariant, not stale `pending`).

## IssueReference (extended)

`tasks/issue_matrix.py:67` NamedTuple.

| Field | Before | After |
|-------|--------|-------|
| `number` | ✓ | ✓ |
| `first_line_context` | ✓ | ✓ |
| `source_file` | — | **added** (FR-013) |

- **Detection (FR-012)**: the single `_GH_ISSUE_PATTERN` also matches same-repo GitHub issue URLs; cross-repo URLs are not matched.
- **Round-trip**: `to_dict`/`from_dict` carry `source_file`.
- **Dedup (D7)**: multi-file discovery preserves first-occurrence provenance (a number in N files retains its first `source_file`); cross-repo URLs never create a required matrix row.

## Terminology artifacts (IC-01)

- **ADR** `docs/adr/3.x/2026-07-30-1-consolidated-write-surface-and-consolidate-terminology.md` — design + canonical-term decision (D4).
- **Glossary** `docs/context/orchestration.md` — `consolidate` canonical for the lane-consolidation sense; that sense of "merge" marked legacy alias with "do NOT use when" guards.
- **Drift guard** — curated forbidden lane-consolidation-sense phrasings + baseline allow-set in `test_no_legacy_terminology.py` (D5).
