# Tasks: Canonical Path-Trust & Guard-Capability Seams

**Mission:** `canonical-seams-path-trust-guard-capability-01KVBBT6` (mid8 `01KVBBT6`)
**Branch:** `feat/canonical-seams-path-trust-guard-capability` → merge target **main**
**Spec:** [spec.md](./spec.md) · **Plan:** [plan.md](./plan.md) · **Research:** [research.md](./research.md)

Six work packages from the Implementation Concern Map. Goal A = WP01→WP02 (+ WP04's merge.py validator half);
Goal B = WP03→WP04; Goal C = WP05, WP06 (independent). **WP04 is the sole owner of `merge.py`** (carries both
its Goal-A validator delegate and its Goal-B helper collapse — D-6, overlap-free ownership).

## Dependency DAG

```
WP01 (validator + primitive)  ──┬──▶ WP02 (migrate validators)
                                └──▶ WP04 (merge.py: validator delegate + helper collapse)
WP03 (ensure_within_any)  ──────────▶ WP04
WP05 (un-mask CI gate)        [independent]
WP06 (re-key ratchet pins)    [independent]
```

MVP / first lane: **WP01** (the canonical seam everything else targets). WP03/WP05/WP06 parallelize immediately;
WP02 after WP01; WP04 after WP01+WP03.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | TDD: union-of-real-format-slugs + traversal-reject tests (red) | WP01 | |
| T002 | Implement `assert_safe_path_segment` in core/paths.py (reconcile regex, keep traversal guard) | WP01 | |
| T003 | Wire validator into `primary_feature_dir_for_mission` + `resolve_mission_read_path` | WP01 | |
| T004 | NFR-002 test: rejection fires INSIDE the primitive (topology-true) | WP01 | |
| T005 | ruff+mypy ≤15; confirm no caller re-routing | WP01 | |
| T006 | Delegate `transaction.py::_validate_safe_segment` (keep BookkeepingError) | WP02 | [P] |
| T007 | Delegate `aggregate.py::_validate_mission_slug` (keep InvalidMissionSlug) | WP02 | [P] |
| T008 | Delegate `review/cycle.py::_validate_segment` (keep ReviewCycleError) — brownfield +1 | WP02 | [P] |
| T009 | Tests: each call site preserves its domain exception type | WP02 | |
| T010 | ruff+mypy ≤15; retrospective/schema.py:203 left untouched (documented scope-out) | WP02 | |
| T011 | TDD: ensure_within_any tests (roots / files arm / strict=False) | WP03 | [P] |
| T012 | Implement `ensure_within_any(path, *, roots, files=())` in core/utils.py | WP03 | |
| T013 | ruff+mypy ≤15; ensure_within_directory unchanged | WP03 | |
| T014 | Delegate `_validate_mission_slug_path_segment` (keep ValueError) + FR-003 sibling-seam reject test | WP04 | |
| T015 | dry-run/abort sites catch the ValueError → clean `--abort` diagnostic | WP04 | |
| T016 | Collapse `_assert_status_path_within_target_surface` → ensure_within_any | WP04 | |
| T017 | Collapse `_assert_bookkeeping_snapshot_path_is_trusted` → ensure_within_any (files arm) | WP04 | |
| T018 | Keep `_assert_status_surface_path_is_trusted` XOR conditional caller (NO union-widening) + test | WP04 | |
| T019 | Behavior-preserving merge suites green + ruff/mypy ≤15 | WP04 | |
| T020 | Widen `core_misc` filter (status/**, coordination/**, core/worktree.py) | WP05 | [P] |
| T021 | Meta-test: guarded-surface→architectural-shard coverage (path-glob keyed, drift-proof) | WP05 | |
| T022 | Validate against the live lifecycle_events scenario | WP05 | |
| T023 | ruff+mypy on the meta-test | WP05 | |
| T024 | Re-key `_ALLOWED_SITES`/`_SHORTID_ALLOWED_SITES`/count baselines → AST/qualname composite | WP06 | [P] |
| T025 | +1-line-drift test: semantic-neutral insertion does not flip the ratchet | WP06 | |
| T026 | Leave `test_no_write_side_rederivation._ALLOW_LIST:295` untouched; keep per-site accountability | WP06 | |
| T027 | ruff+mypy ≤15 | WP06 | |

---

## WP01 — Canonical safe-segment validator + primitive wiring

- **Goal:** the single authority. One general safe-path-segment validator in `core/paths.py`, called inside the
  read primitives so every path-assembly caller inherits it. **Lands FIRST.**
- **Priority:** P0 (the seam). **Dependencies:** none.
- **Requirements:** FR-001, FR-004, NFR-002, NFR-006.
- **Independent test:** malformed segment (`../escape`, `a/b`, non-ASCII) rejected when calling
  `primary_feature_dir_for_mission` directly; every real-format value still validates.
- **Prompt:** [tasks/WP01-canonical-validator.md](./tasks/WP01-canonical-validator.md) (~320 lines)

- [x] T001 TDD: union-of-real-format-slugs + traversal-reject tests (red) (WP01)
- [x] T002 Implement `assert_safe_path_segment` in core/paths.py (WP01)
- [x] T003 Wire validator into `primary_feature_dir_for_mission` + `resolve_mission_read_path` (WP01)
- [x] T004 NFR-002 test: rejection fires inside the primitive (topology-true) (WP01)
- [x] T005 ruff+mypy ≤15; confirm no caller re-routing (WP01)

## WP02 — Migrate divergent validators to delegate

- **Goal:** point the divergent segment validators at the canonical one (migrate, don't wrap; C-001).
- **Priority:** P1. **Dependencies:** WP01.
- **Requirements:** FR-002.
- **Independent test:** each call site still raises its domain exception type; existing suites green.
- **Prompt:** [tasks/WP02-migrate-validators.md](./tasks/WP02-migrate-validators.md) (~300 lines)

- [x] T006 Delegate `transaction.py::_validate_safe_segment` (keep BookkeepingError) (WP02)
- [x] T007 Delegate `aggregate.py::_validate_mission_slug` (keep InvalidMissionSlug) (WP02)
- [x] T008 Delegate `review/cycle.py::_validate_segment` (keep ReviewCycleError) (WP02)
- [x] T009 Tests: each call site preserves its domain exception type (WP02)
- [x] T010 ruff+mypy ≤15; retrospective/schema.py:203 untouched (WP02)

## WP03 — `ensure_within_any` kernel containment utility

- **Goal:** one parameterized containment util beside `ensure_within_directory` in `core/utils.py`.
- **Priority:** P0 (independent seam). **Dependencies:** none.
- **Requirements:** FR-005, NFR-001.
- **Independent test:** under-root accept, outside reject, exact-file allowlist accept, strict=False semantics.
- **Prompt:** [tasks/WP03-ensure-within-any.md](./tasks/WP03-ensure-within-any.md) (~240 lines)

- [x] T011 TDD: ensure_within_any tests (roots / files arm / strict=False) (WP03)
- [x] T012 Implement `ensure_within_any(path, *, roots, files=())` in core/utils.py (WP03)
- [x] T013 ruff+mypy ≤15; ensure_within_directory unchanged (WP03)

## WP04 — merge.py: validator delegate + collapse containment helpers (sole merge.py owner)

- **Goal:** carry BOTH merge.py's Goal-A validator delegate and Goal-B helper collapse (D-6 single owner).
- **Priority:** P1. **Dependencies:** WP01, WP03.
- **Requirements:** FR-002 (merge validator), FR-003, FR-006, NFR-001.
- **Independent test:** malformed slug rejected at a `primary_feature_dir_for_mission` sibling seam; the two
  collapsed helpers + the preserved XOR caller behave byte-identically.
- **Prompt:** [tasks/WP04-merge-pathtrust.md](./tasks/WP04-merge-pathtrust.md) (~420 lines)

- [x] T014 Delegate `_validate_mission_slug_path_segment` (keep ValueError) + FR-003 sibling-seam reject test (WP04)
- [x] T015 dry-run/abort sites catch the ValueError → clean `--abort` diagnostic (WP04)
- [x] T016 Collapse `_assert_status_path_within_target_surface` → ensure_within_any (WP04)
- [x] T017 Collapse `_assert_bookkeeping_snapshot_path_is_trusted` → ensure_within_any (files arm) (WP04)
- [x] T018 Keep `_assert_status_surface_path_is_trusted` XOR conditional caller + test (WP04)
- [x] T019 Behavior-preserving merge suites green + ruff/mypy ≤15 (WP04)

## WP05 — Un-mask the architectural CI gate

- **Goal:** the architectural shard runs the FULL `tests/architectural/**` whenever a guarded surface changes.
- **Priority:** P1 (guard-capability; #2023). **Dependencies:** none.
- **Requirements:** FR-007, NFR-004.
- **Independent test:** a `status/**` edit triggers the full architectural shard; a meta-test pins the coverage.
- **Prompt:** [tasks/WP05-unmask-ci-gate.md](./tasks/WP05-unmask-ci-gate.md) (~260 lines)

- [x] T020 Widen `core_misc` filter (status/**, coordination/**, core/worktree.py) (WP05)
- [x] T021 Meta-test: guarded-surface→architectural-shard coverage (path-glob keyed) (WP05)
- [x] T022 Validate against the live lifecycle_events scenario (WP05)
- [x] T023 ruff+mypy on the meta-test (WP05)

## WP06 — Re-key the line-pinned architectural ratchets

- **Goal:** re-key `test_no_worktree_name_guess.py`'s allow-lists to drift-proof AST/qualname composites.
- **Priority:** P1 (guard-capability; #2023). **Dependencies:** none.
- **Requirements:** FR-008, NFR-004.
- **Independent test:** a +1-line drift does not flip the ratchet; only a genuine new offender does;
  `test_no_write_side_rederivation._ALLOW_LIST:295` untouched.
- **Prompt:** [tasks/WP06-rekey-ratchets.md](./tasks/WP06-rekey-ratchets.md) (~260 lines)

- [x] T024 Re-key `_ALLOWED_SITES`/`_SHORTID_ALLOWED_SITES`/count baselines → AST/qualname composite (WP06)
- [x] T025 +1-line-drift test: semantic-neutral insertion does not flip the ratchet (WP06)
- [x] T026 Leave `:295` untouched; keep per-site accountability (WP06)
- [x] T027 ruff+mypy ≤15 (WP06)

---

## Binding discipline (every WP)

- **TDD-first**; topology-true fixtures (full 26-char ULID, real coord-worktree where touched).
- **Behavior-preserving for A/B** (NFR-001): no trusted-root SET changes, no caller re-routing, no
  write-topology/rollback changes. **C is guard-mechanism only** (NFR-004): change how guards are keyed/
  scheduled, not what they assert; the new ratchet/CI-fix must be drift-proof + CI-unmaskable.
- **Validation proven at the PRIMITIVE** not just callers (NFR-002). Regex reconciliation preserves the
  `.`/`..`/`/`/`\` traversal guard + a union-of-real-format-slugs test (NFR-006).
- **C-007 non-goals:** do NOT re-route the ~143 callers or unify the two primitives; do NOT touch
  `status_transition.py:295` (#1716-blocked); `retrospective/schema.py:203` is a documented scope-out.
- `ruff`+`mypy` clean, complexity ≤ 15, no suppressions. **C-008 Fix-don't-litigate.** No version prescription.
