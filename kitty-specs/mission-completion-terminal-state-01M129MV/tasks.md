# Tasks: Mission Completion Terminal State

**Mission**: mission-completion-terminal-state-01M129MV
**Branch**: `fix/mission-completion-terminal-state`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Contracts**: [contracts/](contracts/)

Subtask completion is event-sourced (`spec-kitty agent tasks mark-status Txxx --status done`);
the rows below are reference rows, not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Operator-vs-synthetic provenance discriminator on the canceled event path | WP01 | |
| T002 | Force-cancel-without-note representable as non-operator provenance (FR-003 reachable) | WP01 | |
| T003 | Project `cancellation_reason` + `reason_source` into the reduced snapshot when `lane==canceled` | WP01 | |
| T004 | Update reducer golden tests for the projected slot | WP01 | |
| T005 | Unit tests: `--note` → operator; `--force` w/o note → synthetic | WP01 | |
| T006 | Add `is_acceptable_ending(lane,*,has_provenance)` to `status_lanes.py` | WP02 | |
| T007 | Replace the three `_ACCEPTED_READY_LANES` definitions with the predicate | WP02 | |
| T008 | accept: canceled+provenance → eligible + `canceled_wps` report; else structured blocker | WP02 | |
| T009 | Non-terminal lanes remain blockers; matrices still run (no short-circuit) | WP02 | |
| T010 | Unit test: predicate truth table | WP02 | |
| T011 | Command test: approved+canceled(prov)→eligible + schema; canceled(synthetic)→blocker | WP02 | |
| T012 | Filter canceled WPs from BOTH `all_wp_ids` (executor:1660) and `done_bookkeeping:666` (coord snapshot) | WP03 | [P] |
| T013 | All-canceled lane-skip guard + route `merge_gates.py` dependency gate through predicate (FR-009 merge face) | WP03 | [P] |
| T014 | In-diff real-git integration test: mid-mission cancel whose lane branch exists | WP03 | [P] |
| T015 | Claim gate: provenance param + replace `_SATISFYING_DEPENDENCY_LANES`; wire `workflow_executor.py` (FR-009 claim face) | WP04 | [P] |
| T016 | Test: dependent of canceled(prov) claimable; dependent of canceled(synthetic) still gated; legacy signature compiles | WP04 | [P] |
| T017 | New `tasks_authoring` module: post-integration trigger-phrase detector | WP05 | [P] |
| T018 | Advisory surface warns naming WP+phrase, never blocks; do not touch `mission_finalize.py` | WP05 | [P] |
| T019 | Labeled corpus fixtures (positive #3590 shapes + adversarial negatives) | WP05 | [P] |
| T020 | Tests: 100% recall on positives, 0 false positives on negatives; advisory | WP05 | [P] |
| T021 | Gate-integrity test: canceled+provenance mission still runs & can fail matrices | WP06 | |
| T022 | "Every WP canceled → not complete" explicit-guard test | WP06 | |
| T023 | Pinned-baseline regression (`a59460ec15`) across named suites; NFR-002 byte-identical | WP06 | |

## Work Packages

### WP01 — Operator-authored provenance capture + reducer projection
- **Goal**: make cancellation provenance operator-authored and readable by accept. FR-001, C-002.
- **Independent test**: canonical `move-task --to canceled --note "…"` marks operator provenance; `--force` without `--note` marks synthetic; the reduced snapshot exposes `cancellation_reason`/`reason_source`.
- **Subtasks**: T001 T002 T003 T004 T005
- **Depends on**: (none) — foundation.
- **Prompt**: [tasks/WP01-provenance-capture.md](tasks/WP01-provenance-capture.md)

### WP02 — Acceptable-ending predicate + accept consumes it
- **Goal**: one `is_acceptable_ending` authority; accept honors canceled+provenance, reports `canceled_wps`, blocks canceled-without-provenance; collapse the 3 duplicated ready-sets. FR-001/002/003/005/006, NFR-003.
- **Independent test**: predicate truth table; command test approved+canceled(prov)→eligible with `canceled_wps` schema, canceled(synthetic)→blocker.
- **Subtasks**: T006 T007 T008 T009 T010 T011
- **Depends on**: WP01.
- **Prompt**: [tasks/WP02-acceptable-ending-accept.md](tasks/WP02-acceptable-ending-accept.md)

### WP03 — Merge WP-granular exclusion of canceled work packages
- **Goal**: exclude canceled WPs from merge's per-WP done/review assertions and order at BOTH derivations (`executor.py:1660` + `done_bookkeeping.py:666`); skip a lane branch only when all its WPs are canceled; route `merge_gates.py` dependency gate through the predicate (FR-009 merge face); retain audit. FR-004, FR-009 (merge), SC-001.
- **Independent test**: in-diff real-git integration test — mid-mission cancel whose lane branch exists → survivors integrate, canceled skipped (no `canceled->done`), dependent-of-canceled not stranded at merge.
- **Subtasks**: T012 T013 T014
- **Depends on**: WP02.
- **Prompt**: [tasks/WP03-merge-canceled-exclusion.md](tasks/WP03-merge-canceled-exclusion.md)

### WP04 — Dependency-on-canceled closure (claim gate)
- **Goal**: a canceled+provenance dependency no longer strands its dependent at claim time; replace `_SATISFYING_DEPENDENCY_LANES` with the shared authority and wire provenance through `workflow_executor.py`. FR-009 (claim), SC-005. (Merge face is WP03; runtime `next`/orchestrator callers deferred — research.md R5.)
- **Independent test**: dependent of canceled(prov) is claimable and can reach an acceptable ending; dependent of canceled(synthetic) still gated; legacy lane-only signature still compiles.
- **Subtasks**: T015 T016
- **Depends on**: WP02.
- **Prompt**: [tasks/WP04-dependency-canceled-closure.md](tasks/WP04-dependency-canceled-closure.md)

### WP05 — Advisory authoring-time un-terminable-work warning
- **Goal**: warn at authoring time when a WP's acceptance criteria are only observable post-integration; advisory, never blocks. FR-007, FR-008, SC-003. **Independent of WP01–WP04.**
- **Independent test**: fixed labeled corpus — 100% recall on positive fixtures, 0 false positives on adversarial negatives; authoring still completes.
- **Subtasks**: T017 T018 T019 T020
- **Depends on**: (none).
- **Prompt**: [tasks/WP05-authoring-warning.md](tasks/WP05-authoring-warning.md)

### WP06 — Regression + gate-integrity harness
- **Goal**: pin the NFR-001 baseline and prove no gate regression; canceled-terminal must not short-circuit sibling matrices; "every WP canceled → not complete". NFR-001, NFR-002, SC-004.
- **Independent test**: gate-integrity test fails when a matrix is bypassed; baseline suites green vs `a59460ec15`.
- **Subtasks**: T021 T022 T023
- **Depends on**: WP01, WP02, WP03, WP04.
- **Prompt**: [tasks/WP06-regression-gate-integrity.md](tasks/WP06-regression-gate-integrity.md)

## Dependency graph

```
WP01 ─▶ WP02 ─┬▶ WP03 ─┐
              └▶ WP04 ─┼▶ WP06
WP05 (independent) ────┘
```

## MVP

**WP01 → WP02** is the MVP: it makes an already-stuck mission (a canceled-with-provenance WP)
complete honestly (#2945). WP03/WP04 extend the fix to merge and the dependency gate; WP05 is
the preventive warning; WP06 is the safety net.
