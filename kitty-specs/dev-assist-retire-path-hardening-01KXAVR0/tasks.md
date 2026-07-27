# Tasks: Dev-Assist Retirement + Path-Validation Hardening

**Mission**: `dev-assist-retire-path-hardening-01KXAVR0` | **Branch**: `feat/dev-assist-retire-path-hardening`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Branch Strategy

Planning artifacts were generated on `feat/dev-assist-retire-path-hardening` (off `main`). Each WP's execution worktree is allocated per computed lane from `lanes.json`; completed changes merge back into `feat/dev-assist-retire-path-hardening`, which is PR'd to `main` at close. The operator performs the mainline merge.

## Overview

Five work packages derived from the plan's Implementation Concern Map. WP01 (security) is the highest priority and is independent. WP02/WP03 retire/narrow development-assist tests with coverage proven by a standing guard first. WP04/WP05 consolidate the fragmented per-family compat batteries. All five have disjoint `owned_files` and no hard ordering (parallelizable); WP04/WP05 reuse the consolidated-guard pattern documented in the plan.

| WP | Title | Concern | Tracker | Depends |
|----|-------|---------|---------|---------|
| WP01 | Path-validation security hardening | IC-01 | #2073 | — |
| WP02 | Runtime-bridge dev-assist retire/narrow | IC-02, IC-05 | #2557 | — |
| WP03 | Sibling-mission dev-assist retire/narrow | IC-03, IC-05 | #2076 | — |
| WP04 | Merge-family compat-surface consolidation | IC-04, IC-05 | #2565 | — |
| WP05 | Tasks-family consolidated guard + lighter seams | IC-04, IC-05 | #2565 | — |
| WP06 | Tasks-family heavy-seam triage + wave1 reconcile | IC-04, IC-05 | #2565 | WP05 |

> **WP05 split (post-tasks squad):** WP05 was undersized 2–3× (69 of 92 seam test-functions + ~60 KB wave1 reconcile) → split. `owned_files` must be disjoint, so the split is by seam-file group (not by concern): WP05 owns the consolidated guard + the 3 lighter seams; WP06 owns the 3 heavy seams + the wave1 reconcile and depends on WP05's guard (coverage-before-deletion).
> **WP01 scope (operator):** hardens the validator function + de-masks its tests; runtime **wiring is deferred** — `validate_deliverables_path` has no production callers and wiring overlaps the ship-code-as-assets doctrine design (#2539 / #2536). Latent hardening, stated honestly.

## Cross-cutting invariants (apply to every retirement WP)

- **Coverage before deletion (C-002)**: no test is removed until its invariant is proven subsumed by a NAMED standing guard (symbol-set membership or set-equality). Cite the guard in the commit.
- **Anti-vacuity (NFR-002, SC-004)**: after retirement/consolidation, a planted regression (accepted malicious path; silent copy-instead-of-delegate re-export) must still trip a retained standing guard.
- **No new masking (NFR-003)**: zero new xfail/skip masks, `file:line` ratchets, or wiring-only assertions.
- **Green suites**: the full pre-existing runtime / architectural / doctor / merge suites stay green after each WP.

---

## WP01 — Path-validation security hardening

Prompt: [tasks/WP01-path-validation-hardening.md](./tasks/WP01-path-validation-hardening.md)

- [x] T001 Write the red-first strict acceptance suite: replace the 8 `pytest.xfail()` masks + 5 assertion-free tests in `test_path_validation.py` with strict `assert not is_valid` (verified red against today's validator).
- [x] T002 Harden `validate_deliverables_path`: reject `..`/escape (normalize), empty/whitespace, null byte, `~`/home, dot-only, absolute-after-normalize; resolve symlinks and confirm containment; case-normalize the kitty-specs check.
- [x] T003 Preserve legitimate paths: `docs/research/<x>/`, `research-outputs/<x>/` still valid.
- [x] T004 Anti-vacuity: a reintroduced accepted-malicious-path re-reds the suite; full green after fix.

## WP02 — Runtime-bridge dev-assist retire/narrow

Prompt: [tasks/WP02-runtime-bridge-retire.md](./tasks/WP02-runtime-bridge-retire.md)

- [x] T001 RETIRE the three pure family-guard duplicates (`test_bridge_cores.py::test_tracked_guard_and_parse_symbols_are_native_delegates` + `_TRACKED_NATIVE_DELEGATES`; `test_bridge_retrospective.py::...compat_guarded_names`; `test_bridge_composition.py::...compat_guarded_names`) — cite `test_bridge_compat_surface.py` coverage.
- [x] T002 RETIRE the inert `test_bridge_parity.py::test_nfr006_timing_seed`.
- [x] T003 NARROW `test_bridge_io.py::...compat_guarded_names` to iterate only `_PUBLIC_RELOCATED_NAMES` (the 2 public symbols the family guard omits); rename accordingly.
- [x] T004 KEEP `test_bridge_cores.py::test_untracked_parse_helpers_are_identity_reexports` (unique); re-point the `test_seam_defines_every_relocated_symbol` docstrings that reference removed assertions (FR-006).
- [ ] T005 Anti-vacuity + green: planted silent re-export trips the family guard; runtime suite green.

## WP03 — Sibling-mission dev-assist retire/narrow

Prompt: [tasks/WP03-sibling-mission-retire.md](./tasks/WP03-sibling-mission-retire.md)

- [x] T001 RETIRE `test_doctor_shim_reexports.py::test_app_is_a_typer_group_with_seventeen_commands` (subsumed by `test_doctor_cli_surface_golden.py` frozenset-equality) + `::test_pointer_comment_references_issue_2059` (comment-content pin).
- [x] T002 NARROW the doctor golden `test_registered_command_names_are_exactly_the_frozen_sixteen` (drop redundant `len==17`; rename off the "sixteen"/17 drift).
- [x] T003 RETIRE/fold `test_mission_shim_reexports.py::test_record_analysis_shim_gaps_closed` (one-shot; symbols already in `_RECORD_ANALYSIS` battery); dedupe the `test_commit_router_planning_residue.py` presence overlap (keep `__module__`-ownership + AST import-source + INV-8).
- [x] T004 Anti-vacuity + green: the golden set-equality still catches the drift the retired count would have; doctor/mission suites green.

## WP04 — Merge-family compat-surface consolidation

Prompt: [tasks/WP04-merge-consolidation.md](./tasks/WP04-merge-consolidation.md)

- [x] T001 Author one consolidated `tests/merge/test_merge_compat_surface.py` guard over a `{symbol→residual-module}` map (NOT a flat union — `preflight` maps to two residuals; each symbol confirmed an identity re-export, not a native redefine). Real inventory = 8 identity functions across 7 files under 4 names (`test_shim_re_exports_the_same_object` ×5, `..._bake_entrypoint`, `..._preflight_object`, `..._push_preflight_object`; `forecast` has none). Assert superset of the retired set.
- [x] T002 Retire those 8 identity functions + the tautological byte-identical-literal pins in `test_constants_seam.py`; **consolidate the ×8 byte-identical `test_<seam>_does_not_import_the_command_shim` guards into ONE parametrized guard** (do not keep 8 copies); KEEP each seam file's functional + external-contract-literal tests.
- [x] T003 Verify superset coverage (no dropped private symbol) + anti-vacuity (planted broken re-export trips the consolidated guard); merge suite green.

## WP05 — Tasks-family consolidated guard + lighter-seam retirement

Prompt: [tasks/WP05-tasks-consolidation-guard.md](./tasks/WP05-tasks-consolidation-guard.md)

- [x] T001 Author one consolidated `test_tasks_compat_surface.py` guard over a `{symbol→residual}` map covering ALL 6 seams' binding symbols (identity-verified; superset-asserted) — the standing authority WP06 depends on.
- [x] T002 Retire the lighter seams' (`finalize`, `map_requirements`, `shared`) identity batteries + `test_move_set_matches_*` pins + `assert_called` interception proofs (15+18+18).
- [x] T003 Verify the guard covers these 3 seams' symbols + anti-vacuity (planted broken re-export trips it); touched suites green.

## WP06 — Tasks-family heavy-seam triage + wave1 reconcile

Prompt: [tasks/WP06-tasks-heavy-seam-triage.md](./tasks/WP06-tasks-heavy-seam-triage.md) · **depends on WP05**

- [x] T001 Retire the heavy seams' (`status_cmd`, `move_task`, `mark_status`) identity batteries + exact-set pins + `assert_called` interception proofs (18+22+27=67), each per-scenario coverage-verified against WP05's guard or a behavioural test.
- [x] T002 Reconcile wave1 `*_orchestration.py` ↔ wave2 `*_seam.py` (read-only): confirm no observable-contract scenario is dropped; keep a narrow observable test for any gap.
- [x] T003 Verify superset (no dropped private symbol) + anti-vacuity; `tests/specify_cli/cli/commands/agent/` suite green.
