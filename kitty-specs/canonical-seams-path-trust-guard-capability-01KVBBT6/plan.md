# Implementation Plan: Canonical Path-Trust & Guard-Capability Seams

**Branch**: `feat/canonical-seams-path-trust-guard-capability` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/spec.md`
**Mission ID**: `01KVBBT6FEQ01NHNSQD7X8JTPE` (mid8 `01KVBBT6`)

## Summary

Bind path-trust to single canonical seams and close a maskable CI gate. **Goal A:** one general safe-path-segment
validator in `core/paths.py`, called inside the read primitives (`primary_feature_dir_for_mission` +
`resolve_mission_read_path`) so all callers inherit it; the three divergent validators (`merge.py`,
`coordination/transaction.py`, `status/aggregate.py`) delegate. **Goal B:** one `ensure_within_any(path, *, roots,
files=())` in `core/utils.py`; the two non-conditional merge containment helpers delegate; the worktrees-XOR-kitty-specs
helper stays a conditional caller. **Goal C (folded in — see C-003 decision):** un-mask the architectural CI gate
(widen the `core_misc` path filter) + re-key the non-#1716 line-number ratchet pins to AST/qualname composites.
Behavior-preserving throughout; the proof is verification-at-the-primitive plus a union-of-real-format-slugs test.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib only for the seams (`re`, `pathlib`, `tokenize`/`ast` for the ratchet re-key); existing `specify_cli.core` modules; GitHub Actions (`dorny/paths-filter`) for the CI filter
**Storage**: N/A (no data store; filesystem path composition only)
**Testing**: `pytest` (`-m fast` / `-m architectural` profiles), topology-true fixtures (full 26-char ULID, real coord-worktree where the seam touches it); TDD-first; `ruff` + `mypy` zero-issue gate
**Target Platform**: Linux/macOS dev + CI (cross-platform path semantics)
**Project Type**: single (CLI tool + its CI/test harness)
**Performance Goals**: N/A (validation is O(1) per call; no hot path regression)
**Constraints**: behavior-preserving (NFR-001 — no trusted-root SET changes, no caller re-routing, no write-topology/rollback changes); complexity ≤ 15; no suppressions (`# noqa`/`# type: ignore`); the new guards must themselves be drift-proof + CI-unmaskable (NFR-004)
**Scale/Scope**: ~5–7 WPs across `core/paths.py`, `core/utils.py`, `missions/_read_path_resolver.py`, `cli/commands/merge.py`, `coordination/transaction.py`, `status/aggregate.py`, `.github/workflows/ci-quality.yml`, `tests/architectural/test_no_worktree_name_guess.py`; ~75–143 inheriting call sites (not re-routed — they inherit via the primitive)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* — charter context: `compact`.

- **Canonical sources discipline** — PASS. Edits target `src/` runtime + `core/` Shared Kernel + the CI/test
  harness; no generated agent copies touched (C-005).
- **No new authority / no parallel mechanism** — PASS. One validator, one containment util; divergent validators
  *migrate* (delegate/delete), they do not coexist as wrappers (C-001; #1868 spine).
- **Terminology canon** — PASS. "Mission" terminology; no `feature*` aliases introduced (the existing
  `*_feature_dir_for_mission` names are pre-existing API, not introduced here).
- **Behavior-preserving** — PASS by construction (NFR-001); A/B change *where* a decision lives, C changes *how*
  guards are keyed, neither changes *what* is decided/asserted.
- **No charter violations** → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/canonical-seams-path-trust-guard-capability-01KVBBT6/
├── plan.md              # This file
├── research.md          # Phase 0 — census re-verification + C-003 decision
├── research/            # pre-spec investigation basis (00-investigation-synthesis.md)
├── spec.md              # FR/NFR/C + success criteria
├── contracts/           # Phase 1 — seam signatures + CI invariant
├── data-model.md        # Phase 1 — (no new entities; documents the seam objects)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   ├── paths.py                      # Goal A: NEW canonical safe-segment validator (the authority)
│   └── utils.py                      # Goal B: NEW ensure_within_any(path, *, roots, files)
├── missions/
│   └── _read_path_resolver.py        # Goal A: call validator in primary_feature_dir_for_mission + resolve_mission_read_path
├── cli/commands/
│   └── merge.py                      # Goal A: _validate_mission_slug_path_segment delegates; Goal B: 2 helpers delegate, XOR helper conditional caller; dry-run/abort clean-diagnostic
├── coordination/
│   └── transaction.py                # Goal A: _validate_safe_segment delegates (keeps BookkeepingError wrap)
└── status/
    └── aggregate.py                  # Goal A: _validate_mission_slug delegates (keeps InvalidMissionSlug)

.github/workflows/
└── ci-quality.yml                    # Goal C: widen core_misc filter (status/**, coordination/**, core/worktree.py)

tests/architectural/
└── test_no_worktree_name_guess.py    # Goal C: re-key line-pinned allow-lists to AST/qualname composites
```

**Structure Decision**: Single-project layout. The two canonical seams live in the Shared Kernel
(`core/paths.py`, `core/utils.py`); consumers migrate to them. CI/test-harness edits are isolated to two files.

## Complexity Tracking

*No charter violations — none required.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs (one IC may split into several,
> or merge). Ownership notes below keep `owned_files` overlap-free (D-6): **`merge.py` is owned by exactly one WP**
> that carries both its Goal-A validator-delegate edit and its Goal-B helper-collapse edit.

### IC-A1 — Canonical safe-segment validator (the authority)
- **Purpose**: Create the single general safe-path-segment validator in `core/paths.py` and wire it into the read
  primitives so every path-assembly caller inherits it.
- **Relevant requirements**: FR-001, FR-004, NFR-002, NFR-006.
- **Affected surfaces**: `core/paths.py` (new validator), `missions/_read_path_resolver.py`
  (`primary_feature_dir_for_mission`, `resolve_mission_read_path`).
- **Sequencing/depends-on**: none (lands FIRST — the seam the migrations target).
- **Risks**: regex reconciliation must preserve the traversal guard AND admit every real-format value (ULID,
  `<slug>-<mid8>`, numeric-prefix, bare mid8) — union test pins it; `transaction.py` uses it for `mission_id`/`mid8`
  too, so it is a *segment* validator, not slug-only.

### IC-A2 — Migrate the divergent validators to delegate
- **Purpose**: Point `merge.py::_validate_mission_slug_path_segment`, `coordination/transaction.py::_validate_safe_segment`,
  and `status/aggregate.py::_validate_mission_slug` at the canonical validator (delegate or delete), preserving each
  call site's existing exception type (`ValueError` / `BookkeepingError` wrap / `InvalidMissionSlug`).
- **Relevant requirements**: FR-002, FR-003, C-001.
- **Affected surfaces**: `coordination/transaction.py`, `status/aggregate.py`, and `merge.py` (validator half — see
  ownership note: the merge.py edits are owned by one WP with IC-B2).
- **Sequencing/depends-on**: IC-A1.
- **Risks**: the `merge.py` dry-run/abort sites (`_resolve_mission_slug` → :3100/:3194/:3212) must catch the
  validator `ValueError` and render a clean diagnostic (keep `--abort` UX). FR-003 proof test rejects a malformed
  slug at a `primary_feature_dir_for_mission` sibling seam (`:828`/`:2382`).

### IC-B1 — `ensure_within_any` containment utility
- **Purpose**: Add `ensure_within_any(path, *, roots, files=())` to `core/utils.py` (resolve(strict=False) +
  is_relative_to over roots + exact-file membership), beside `ensure_within_directory`.
- **Relevant requirements**: FR-005, NFR-001.
- **Affected surfaces**: `core/utils.py`.
- **Sequencing/depends-on**: none (independent of IC-A*).
- **Risks**: standardize on `resolve(strict=False)`; keep `ensure_within_directory` for single-root callers.

### IC-B2 — Collapse the merge containment helpers
- **Purpose**: The two non-conditional helpers (`_assert_status_path_within_target_surface`,
  `_assert_bookkeeping_snapshot_path_is_trusted` — with its `files=` arm) delegate to `ensure_within_any`; the
  conditional `_assert_status_surface_path_is_trusted` (worktrees XOR kitty-specs) stays a conditional caller that
  selects its single root then delegates — **NO union-widening**.
- **Relevant requirements**: FR-006, NFR-001.
- **Affected surfaces**: `merge.py` (helper half — owned by the SAME WP as IC-A2's merge.py edits).
- **Sequencing/depends-on**: IC-B1.
- **Risks**: behavior byte-identical; the XOR helper must not be folded into a union (preserves the reject of a
  kitty-specs-resolving path while under-worktrees).

### IC-C1 — Un-mask the architectural CI gate
- **Purpose**: Make the `integration-tests-core-misc (architectural)` shard run the full `tests/architectural/**`
  whenever a guarded write-side surface changes — add `src/specify_cli/status/**`, `src/specify_cli/coordination/**`,
  `src/specify_cli/core/worktree.py` to the `core_misc` filter (`ci-quality.yml:~174`); add a meta-test pinning the
  trigger coverage so a future filter edit cannot silently re-open the mask.
- **Relevant requirements**: FR-007, NFR-004 (#2017 B8 / #2023).
- **Affected surfaces**: `.github/workflows/ci-quality.yml`, a new meta-test under `tests/architectural/`.
- **Sequencing/depends-on**: none.
- **Risks**: the meta-test must read the workflow YAML and assert the guarded-surface→architectural-shard coverage
  without becoming brittle itself (key on filter-name + path-glob membership, not line numbers).

### IC-C2 — Re-key the non-#1716 line-number ratchet pins
- **Purpose**: Re-key `test_no_worktree_name_guess.py`'s `_ALLOWED_SITES` / `_SHORTID_ALLOWED_SITES` / count
  baselines to an AST/qualname + normalized-token-line composite (reuse the machinery in the sibling
  `test_no_write_side_rederivation.py`); add a +1-line-drift test proving a semantic-neutral edit no longer flips it.
- **Relevant requirements**: FR-008, NFR-004, C-007 (leave `test_no_write_side_rederivation._ALLOW_LIST:295` — the
  #1716-blocked pin — untouched).
- **Affected surfaces**: `tests/architectural/test_no_worktree_name_guess.py`.
- **Sequencing/depends-on**: none.
- **Risks**: the test already has stale-detection meta-tests; the re-key must keep per-site accountability (don't
  collapse to a count-only baseline) and must not disturb `:295`.

## Post-Planning Brownfield Check (2026-06-17)

Standing pre-tasks scan over the touched surfaces. Outcome:

### Foldable-issue search — CLEAN
No new foldable issues beyond the matrix. `#2022` (primary), `#2007`/`#1827` (cross-ref/out-of-scope),
`#2017`-B8/`#2023` (Goal C) already captured. Tracker matrix is complete.

### Split-brain / logical-duplication scan — SCOPE UNDERSIZED (expand FR-002; flag FR-006)
The spec's "3 divergent validators" undersizes (the recurring "spec/plan always undersizes scope" pattern). The
mission-slug/segment validator family actually has **five** instances:
| Validator | Regex | Raises | Disposition |
|-----------|-------|--------|-------------|
| `merge.py:774 _validate_mission_slug_path_segment` | `^[A-Za-z0-9_-]+$` | `ValueError` | **migrate (FR-002)** |
| `coordination/transaction.py:168 _validate_safe_segment` | `^[A-Za-z0-9][A-Za-z0-9._-]*$` | `BookkeepingError` | **migrate (FR-002)** |
| `status/aggregate.py:347 _validate_mission_slug` | `^[A-Za-z0-9_-]+$` | `InvalidMissionSlug(ValueError)` | **migrate (FR-002)** |
| `review/cycle.py:75 _validate_segment` | `^[A-Za-z0-9][A-Za-z0-9._-]*$` | `ReviewCycleError` | **ADDED → migrate (FR-002)** — identical safe-segment idiom |
| `retrospective/schema.py:203 _validate_safe_slug` | `^[A-Za-z0-9._-]{1,128}$` (Pydantic) | `ValueError` | **borderline — scope-out by default** (Pydantic-bound, length-capped, different mechanism); fold only if tasks finds it clean |

Out-of-scope (different domains, NOT mission-slug segments): `sync/git_metadata.py::_validate_repo_slug`,
`doctrine/sources/api_source.py::_SAFE_FILENAME`, `invocation/record.py::_ULID_RE`, WP-id / commit-hash regexes.

**Containment guards (FR-006):** beyond merge.py's 3, `coordination/transaction.py` has additional
`is_relative_to`-against-worktree guards (`_confine_path_to_worktree` :364, `_resolve_confined_artifact_path` :383,
+ :462/:964). These sit in the **#1716-deferred write-target topology** area → **scope-out by default (C-007)** with a
fold-candidate note (they could later delegate to `ensure_within_any(roots=[worktree_root])`). Cross-domain
containment (`skills/verifier.py`, `skills/command_installer.py`, `doctrine/sources/api_source.py`,
`intake_sources.py`) is **out** (different trusted roots) — future `ensure_within_any` consumers, not this mission.

**LOC/god-module:** `merge.py` 3447 / `transaction.py` 1176 are god-modules, but this mission only touches bounded
helper regions; no de-godding in scope.

### Deprecation check — NONE DUE
No deprecation is due for removal in the touched surfaces. The `safe_commit_cmd.py --to-branch` v3.3 deprecation is
the routing-bug mechanism (logged to #2017, comment-4733897389) and is intentionally **not** removed here.
`transaction.py:316/324` is a once-only deprecation-warning emitter (infra, not a due removal).

### Net effect on scope
- **FR-002 migration list grows by one** (`review/cycle.py:75`), keeping its `ReviewCycleError` wrap; `retrospective/schema.py:203` is a documented borderline (default scope-out).
- **FR-006 unchanged** (the transaction.py confinement guards are #1716-deferred, C-007) — recorded as a fold candidate for a later topology mission.
- No version/deprecation removal. `/spec-kitty.tasks` should reflect the FR-002 +1 validator in the IC-A2 ownership/owned_files.

## Branch contract (restated)

Current branch: `feat/canonical-seams-path-trust-guard-capability`. Planning/base branch for this mission:
`feat/canonical-seams-path-trust-guard-capability`. Final merge target: **main** (PR `feat/…` → main). Matches the
operator's intended landing branch.
