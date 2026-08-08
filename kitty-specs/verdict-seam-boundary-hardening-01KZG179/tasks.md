# Tasks: Verdict-Seam Boundary Hardening

**Mission**: `verdict-seam-boundary-hardening-01KZG179`
**Branch**: `hardening/verdict-seam-facade-followup` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Subtask completion is event-sourced — record with `spec-kitty agent tasks mark-status Txxx --status done`. The rows below are reference rows, not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Import + export full verdict_vocab surface (8 fns + EventVerdict alias + APPROVED/REJECTED/CHANGES_REQUESTED) on `status.__all__` | WP01 | |
| T002 | Export `review_result_from_state` on `status.__all__` (beside `event_sourced_review_result`) | WP01 | |
| T003 | (FR-006 campsite) Rename two drifted reducer tests — name/docstring only, assertions unchanged | WP01 | [P] |
| T004 | Extend façade-adoption test to assert the new exports present | WP01 | |
| T005 | Migrate the 8 verdict_vocab submodule-object consumers to façade symbols | WP02 | |
| T006 | Migrate the 4 collateral submodule-object imports (emit / store×2 / lane_reader) | WP02 | |
| T007 | Campsite: extract `_build_claim_review_override` (cc=13 guard) + `done_bookkeeping:119` → `APPROVED` | WP02 | |
| T008 | Retire the duplicated decode in `_event_sourced_gate_verdict`; delete the false docstring; reconcile reducer docstring | WP02 | |
| T009 | Widen `_is_bypass_import` (submodule-name-targeted) + non-vacuity teeth test | WP02 | |
| T010 | Behavior-preservation tests for the dedup (5 decode cases) | WP02 | |
| T011 | Add a function-level exclusion mechanism to the verdict-seam census | WP03 | |
| T012 | Narrow `verdict_provenance_backfill.py` exclusion to write-side helpers; `_legacy_frontmatter_verdict` surfaces (#3236) | WP03 | |
| T013 | Extend the classifier to recognize helper-constructed readers; `_review_from_frontmatter` surfaces (#3217) | WP03 | |
| T014 | Flip the 3 wholesale-exclusion tests + update census fixture; retain non-vacuity teeth | WP03 | |
| T015 | RED-FIRST: conflict-marked latest review-cycle `.md` + arbiter override → no crash (#3244) | WP04 | |
| T016 | Add `ReviewCycleArtifact.latest_cycle_number()` (filename-only) + hoist review-cycle glob/filename constants (S1192) | WP04 | |
| T017 | Swap `arbiter.py:466-467` to `latest_cycle_number`; leave `.latest`/`from_file` intact (C-004) | WP04 | |
| T018 | Direct micro-test for `latest_cycle_number` (mixed valid + conflict-marked siblings) | WP04 | [P] |
| T020 | Lift `provenance_note` out of the JSON gate; shared helper injects `advisories[]` at 4 emit sites (#3255) | WP05 | |
| T021 | Campsite: `_safe_emit_error_logged` S110 fix (debug-log + rationale) | WP05 | [P] |
| T022 | Test: stranded fixture → advisory in JSON; converged → empty `advisories` | WP05 | |
| T023 | Add `-m stress -n0` serial CI job to `ci-quality.yml` (POSIX-only, mirror `timing-nfr-serial`) (#3256) | WP06 | |
| T024 | Right-size `test_emit_durability.py` durability test out of the fast pool | WP06 | |
| T025 | Correct `pytest.ini:47` stress-marker wording; leave #3235 coordination pointer | WP06 | [P] |

---

## Work Packages

### WP01 — Façade exports (IC-01a) · foundational
**Goal**: Promote the full verdict bridge onto `status.__all__` so every symbol consumers need is a façade export, and land the export *before* WP02's dedup (C-002). **Priority**: P1. **Independent test**: import each promoted symbol from `specify_cli.status`; façade-adoption test green.
**Subtasks**: T001, T002, T003, T004. **Dependencies**: none. **Prompt**: `tasks/WP01-facade-exports.md` (~250 lines).
**Risk**: PR #3209 already merged into base — re-verify the two FR-006 test names before renaming.

### WP02 — Consumer migration + dedup + guard widening (IC-01b)
**Goal**: Migrate all 12 submodule-object imports to façade symbols, retire the duplicated merge-blocking decode, and widen the boundary guard so the bypass is actually caught. **Priority**: P1. **Independent test**: grep shows zero `status.<submodule>` object imports; boundary teeth test flags a synthetic violation; full status suite green.
**Subtasks**: T005, T006, T007, T008, T009, T010. **Dependencies**: **WP01** (export-before-dedup). **Prompt**: `tasks/WP02-consumer-migration-guard.md` (~480 lines).
**Risk**: three cc=15 do-not-touch functions in edited modules — keep diffs surgical.

### WP03 — Census completeness (IC-02) · parallel
**Goal**: Narrow the wholesale module exclusion to function level and teach the classifier to see helper-constructed readers, so #3236+#3217 leave the census fully hardened. **Priority**: P1. **Independent test**: `_legacy_frontmatter_verdict` and `_review_from_frontmatter` appear as reader rows; write-side helpers excluded by name; non-vacuity teeth green.
**Subtasks**: T011, T012, T013, T014. **Dependencies**: none. **Prompt**: `tasks/WP03-census-completeness.md` (~300 lines).

### WP04 — Arbiter resilience (IC-03) · parallel · RED-FIRST
**Goal**: Red-first fix for the conflict-marked-artifact arbiter crash via a filename-only cycle-number resolver. **Priority**: P1. **Independent test**: the red-first regression is RED pre-fix, GREEN post-fix; `.latest`/`from_file` behavior unchanged.
**Subtasks**: T015, T016, T017, T018. **Dependencies**: none. **Prompt**: `tasks/WP04-arbiter-resilience-reader-dedup.md` (~320 lines).
**Note**: #3216 (originally folded here as T019) was descoped — the post-tasks squad found its target reader already retired by the prior mission's WP05 (#3245); #3216 closed as already-resolved.

### WP05 — `accept --json` advisories (IC-04) · parallel
**Goal**: Surface the SC-008 advisory in a uniform top-level `advisories` array at the CLI emit layer. **Priority**: P2. **Independent test**: stranded fixture → advisory present in JSON; converged → empty array.
**Subtasks**: T020, T021, T022. **Dependencies**: none. **Prompt**: `tasks/WP05-accept-json-advisories.md` (~230 lines).

### WP06 — Stress CI lane (IC-05) · parallel · CI-infra
**Goal**: A dedicated `-m stress -n0` serial lane so the heavyweight durability test stops riding the fast pool. **Priority**: P2. **Independent test**: `-m stress` selects the durability test in its own serial job; the fast-pool selector no longer collects it.
**Subtasks**: T023, T024, T025. **Dependencies**: none. **Prompt**: `tasks/WP06-stress-ci-lane.md` (~230 lines).

## Dependency Graph

```
WP01 ──▶ WP02
WP03  ── parallel
WP04  ── parallel (red-first)
WP05  ── parallel
WP06  ── parallel
```

## MVP

WP01+WP02 (the single-authority boundary — the mission's core theme). WP03–WP06 are independent hardening lanes that can proceed concurrently.
