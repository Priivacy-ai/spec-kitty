# Tasks: 3.2.0a6 Tranche 2 Bug Cleanup

**Mission**: `release-3-2-0a6-tranche-2-01KQ9MKP`
**Branch**: `release/3.2.0a6-tranche-2`
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md)

## Branch Strategy

- Planning/base branch: `release/3.2.0a6-tranche-2`
- Final merge target: `release/3.2.0a6-tranche-2`
- Execution worktrees are allocated per computed lane in `lanes.json` after `finalize-tasks`.

## Overview

7 work packages cover the seven issues in scope. Lane A is the foundation/charter chain (sequential). Lanes B–E are independent issues that can run in parallel with Lane A and each other.

```
Lane A (sequential):  WP01 → WP06 → WP07
Lane B (parallel):    WP02
Lane C (parallel):    WP03 → WP04
Lane D (parallel):    WP05
```

WP07 is the capstone — its dependencies (WP01, WP02, WP05, WP06) span lanes; finalize-tasks computes the actual execution-lane mapping.

## Subtask Index

| ID   | Description                                                              | WP    | Parallel |
|------|--------------------------------------------------------------------------|-------|----------|
| T001 | Define schema_version + schema_capabilities canonical map                | WP01  |          |
| T002 | Implement additive metadata.yaml stamp in init                           | WP01  |          |
| T003 | Idempotency + operator-key preservation                                  | WP01  |          |
| T004 | Unit tests: empty dir, hand-edited file, idempotency                     | WP01  | [P]      |
| T005 | Integration test: init then next runs without missing-schema errors      | WP01  |          |
| T006 | CHANGELOG entry for #840                                                 | WP01  | [P]      |
| T007 | Inventory covered --json commands and their stdout writers               | WP02  |          |
| T008 | Add diagnostic-routing helper (default stderr, optional envelope nest)   | WP02  |          |
| T009 | Refactor sync/auth/tracker print sites to use the helper                 | WP02  |          |
| T010 | Parametrised integration test across 4 SaaS states                       | WP02  | [P]      |
| T011 | Bare-string regression scan of stdout                                    | WP02  | [P]      |
| T012 | CHANGELOG entry + update contracts/json-envelope.md cross-refs           | WP02  | [P]      |
| T013 | Update WPMetadata.resolved_agent() to support 1/2/3/4 colon segments     | WP03  |          |
| T014 | Document defaults table for missing trailing fields                      | WP03  |          |
| T015 | Wire 4-tuple through implement/review prompt context surface             | WP03  |          |
| T016 | Unit tests: 4 arities + empty-positional-segment cases                   | WP03  | [P]      |
| T017 | Integration test: rendered prompt contains supplied model/profile/role   | WP03  |          |
| T018 | Identify rejection event handler and reclaim/regenerate code path        | WP04  |          |
| T019 | Move counter advancement into rejection event handler exclusively        | WP04  |          |
| T020 | Make reclaim/regenerate idempotent (no counter delta, no new artifact)   | WP04  |          |
| T021 | Unit tests: ≥3 reruns of implement leave counter unchanged               | WP04  | [P]      |
| T022 | Integration test: real rejection advances counter exactly once           | WP04  |          |
| T023 | Define ProfileInvocationRecord shape per data-model.md                   | WP05  |          |
| T024 | Hook started-record write into next issuance path                        | WP05  |          |
| T025 | Hook completed/failed-record write into next advance path                | WP05  |          |
| T026 | Surface orphan started records via doctor                                | WP05  |          |
| T027 | Unit tests: pair-matching, orphan observability                          | WP05  | [P]      |
| T028 | Integration test: ≥5 issuances yield ≥95% pairing                        | WP05  |          |
| T029 | charter generate auto-tracks charter.md on success in git repo           | WP06  |          |
| T030 | charter generate fails fast in non-git environment with actionable error | WP06  |          |
| T031 | charter synthesize: identify minimal doctrine artifact set               | WP06  |          |
| T032 | charter synthesize: produce artifacts from canonical inputs              | WP06  |          |
| T033 | Idempotency: synthesize twice yields identical output set                | WP06  |          |
| T034 | Integration test: fresh repo, generate→bundle validate succeeds          | WP06  | [P]      |
| T035 | Integration test: synthesize on fresh project produces expected set      | WP06  | [P]      |
| T036 | Update test_charter_epic_golden_path.py: no doctrine seed, no metadata edit | WP07 |       |
| T037 | Verify under-120s budget on CI for golden-path E2E                       | WP07  |          |
| T038 | Update governance setup docs to remove redundant git add (FR-017)        | WP07  | [P]      |
| T039 | CHANGELOG entry: tranche-2 summary                                       | WP07  | [P]      |
| T040 | Final acceptance pass against spec.md SC-001..SC-008                     | WP07  |          |

---

## WP01 — Init stamps schema_version + schema_capabilities (#840)

- **Goal**: A fresh `spec-kitty init` produces a `.kittify/metadata.yaml` whose `schema_version` and `schema_capabilities` fields satisfy downstream commands without any manual editing.
- **Priority**: P0 (foundation for the fresh-project chain).
- **Independent test**: Init an empty directory; assert `schema_version` and `schema_capabilities` present and valid; run `next` against it without error.
- **Estimated prompt size**: ~400 lines.
- **Prompt**: [tasks/WP01-init-schema-stamp.md](tasks/WP01-init-schema-stamp.md).

Subtasks:

- [ ] T001 Define schema_version + schema_capabilities canonical map (WP01)
- [ ] T002 Implement additive metadata.yaml stamp in init (WP01)
- [ ] T003 Idempotency + operator-key preservation (WP01)
- [ ] T004 Unit tests: empty dir, hand-edited file, idempotency (WP01) [P]
- [ ] T005 Integration test: init then next runs without missing-schema errors (WP01)
- [ ] T006 CHANGELOG entry for #840 (WP01) [P]

Dependencies: none. Risks: overwriting operator-authored fields; mitigated by FR-002 + NFR-008 idempotency tests.

---

## WP02 — Strict JSON envelope on `--json` commands (#842)

- **Goal**: Every covered `--json` command produces stdout that `json.loads` accepts across the four SaaS states; diagnostics route to stderr or into the envelope under a documented key.
- **Priority**: P0 (external script consumers blocked today).
- **Independent test**: Parametrised test runs each covered `--json` command across `disabled` / `unauthorized` / `network-failed` / `authorized-success` and asserts `json.loads(stdout)` succeeds with no bare diagnostic lines on stdout.
- **Estimated prompt size**: ~420 lines.
- **Prompt**: [tasks/WP02-strict-json-envelope.md](tasks/WP02-strict-json-envelope.md).

Subtasks:

- [ ] T007 Inventory covered --json commands and their stdout writers (WP02)
- [ ] T008 Add diagnostic-routing helper (default stderr, optional envelope nest) (WP02)
- [ ] T009 Refactor sync/auth/tracker print sites to use the helper (WP02)
- [ ] T010 Parametrised integration test across 4 SaaS states (WP02) [P]
- [ ] T011 Bare-string regression scan of stdout (WP02) [P]
- [ ] T012 CHANGELOG entry + update contracts/json-envelope.md cross-refs (WP02) [P]

Dependencies: none. Risks: changing diagnostic surface for human users; mitigated by stderr default (humans still see diagnostics in terminal output).

---

## WP03 — Agent identity 4-tuple parser (#833)

- **Goal**: `WPMetadata.resolved_agent()` parses every supported colon arity into the `(tool, model, profile_id, role)` 4-tuple without silent discard, and the implement/review prompts surface all four fields.
- **Priority**: P0 (silent identity loss in production review loops).
- **Independent test**: Unit tests for arities 1/2/3/4 + empty-positional cases; integration test asserts a rendered prompt contains the supplied `model`, `profile_id`, `role` for a 4-arity input.
- **Estimated prompt size**: ~340 lines.
- **Prompt**: [tasks/WP03-agent-identity-4tuple.md](tasks/WP03-agent-identity-4tuple.md).

Subtasks:

- [ ] T013 Update WPMetadata.resolved_agent() to support 1/2/3/4 colon segments (WP03)
- [ ] T014 Document defaults table for missing trailing fields (WP03)
- [ ] T015 Wire 4-tuple through implement/review prompt context surface (WP03)
- [ ] T016 Unit tests: 4 arities + empty-positional-segment cases (WP03) [P]
- [ ] T017 Integration test: rendered prompt contains supplied model/profile/role (WP03)

Dependencies: none. Risks: shifting implicit defaults for partial strings; mitigated by NFR-004 regression tests at every arity.

---

## WP04 — Review-cycle counter advances only on real rejections (#676)

- **Goal**: Re-running `agent action implement` is idempotent for review state; the counter and `review-cycle-N.md` artifacts only change in response to a real reviewer rejection event.
- **Priority**: P0 (review pipeline state corruption).
- **Independent test**: Re-run `implement` ≥ 3 times against a `for_review` WP and assert counter unchanged + zero new artifacts; simulate a real rejection and assert counter advances by exactly one with one matching artifact.
- **Estimated prompt size**: ~360 lines.
- **Prompt**: [tasks/WP04-review-cycle-counter.md](tasks/WP04-review-cycle-counter.md).

Subtasks:

- [ ] T018 Identify rejection event handler and reclaim/regenerate code path (WP04)
- [ ] T019 Move counter advancement into rejection event handler exclusively (WP04)
- [ ] T020 Make reclaim/regenerate idempotent (no counter delta, no new artifact) (WP04)
- [ ] T021 Unit tests: ≥3 reruns of implement leave counter unchanged (WP04) [P]
- [ ] T022 Integration test: real rejection advances counter exactly once (WP04)

Dependencies: WP03 (shared modification surface in `cli/commands/agent/workflow.py`; sequenced to avoid lane conflicts on the same file). Risks: missing a code path that still increments; mitigated by review of every counter mutation site.

---

## WP05 — `next` writes paired profile-invocation lifecycle records (#843)

- **Goal**: Every public action issued by `spec-kitty next` produces a `started` record at issuance time and a paired `completed`/`failed` record at advance time; both share a canonical action identifier; orphans are observable via the doctor surface.
- **Priority**: P0 (no observability for `next` issuances today).
- **Independent test**: Drive ≥ 5 issued actions; assert ≥ 95% pair-match rate; simulate mid-cycle stop and assert orphan listed by doctor.
- **Estimated prompt size**: ~430 lines.
- **Prompt**: [tasks/WP05-next-lifecycle-records.md](tasks/WP05-next-lifecycle-records.md).

Subtasks:

- [ ] T023 Define ProfileInvocationRecord shape per data-model.md (WP05)
- [ ] T024 Hook started-record write into next issuance path (WP05)
- [ ] T025 Hook completed/failed-record write into next advance path (WP05)
- [ ] T026 Surface orphan started records via doctor (WP05)
- [ ] T027 Unit tests: pair-matching, orphan observability (WP05) [P]
- [ ] T028 Integration test: ≥5 issuances yield ≥95% pairing (WP05)

Dependencies: none. Risks: orphan flood on agent crashes; mitigated by NFR-006 pairing budget + doctor visibility.

---

## WP06 — Charter fresh-project flow: generate auto-track + synthesize (#841 + #839)

- **Goal**: On a fresh project, `charter generate` produces an artifact that `charter bundle validate` accepts without manual `git add`, and `charter synthesize` runs successfully without any hand-seeded `.kittify/doctrine/`.
- **Priority**: P0 (governance setup blocked on fresh projects).
- **Independent test**: Fresh git repo: `init → charter setup → charter generate → charter bundle validate → charter synthesize` all exit 0 with no manual commands; non-git directory: `charter generate` exits non-zero with a specific actionable error string.
- **Estimated prompt size**: ~520 lines (largest WP — borderline acceptable; see WP rationale).
- **Prompt**: [tasks/WP06-charter-fresh-project-flow.md](tasks/WP06-charter-fresh-project-flow.md).

Subtasks:

- [ ] T029 charter generate auto-tracks charter.md on success in git repo (WP06)
- [ ] T030 charter generate fails fast in non-git environment with actionable error (WP06)
- [ ] T031 charter synthesize: identify minimal doctrine artifact set (WP06)
- [ ] T032 charter synthesize: produce artifacts from canonical inputs (WP06)
- [ ] T033 Idempotency: synthesize twice yields identical output set (WP06)
- [ ] T034 Integration test: fresh repo, generate→bundle validate succeeds (WP06) [P]
- [ ] T035 Integration test: synthesize on fresh project produces expected set (WP06) [P]

Dependencies: WP01 (fresh-project init is the precondition for fresh-project charter flow). Risks: scope creep into doctrine subsystem; mitigated by Risk Map rule "do not introduce new doctrine subsystems" + escalation gate.

---

## WP07 — Consolidated golden-path E2E + docs sync

- **Goal**: The end-to-end golden-path test exercises the full fresh-project chain through public CLI only and passes within the 120s CI budget; user-facing docs match the new CLI invariants.
- **Priority**: P0 (proves the tranche-level acceptance criteria).
- **Independent test**: `pytest tests/e2e/test_charter_epic_golden_path.py -v` passes under 120s in CI; the test no longer hand-seeds doctrine and no longer hand-edits metadata.
- **Estimated prompt size**: ~310 lines.
- **Prompt**: [tasks/WP07-golden-path-e2e-docs.md](tasks/WP07-golden-path-e2e-docs.md).

Subtasks:

- [ ] T036 Update test_charter_epic_golden_path.py: no doctrine seed, no metadata edit (WP07)
- [ ] T037 Verify under-120s budget on CI for golden-path E2E (WP07)
- [ ] T038 Update governance setup docs to remove redundant git add (FR-017) (WP07) [P]
- [ ] T039 CHANGELOG entry: tranche-2 summary (WP07) [P]
- [ ] T040 Final acceptance pass against spec.md SC-001..SC-008 (WP07)

Dependencies: WP01, WP02, WP05, WP06 (all are exercised by the consolidated E2E and the docs sync). Risks: flakiness from real charter doctrine seed work; mitigated by Assumption A2 (public CLI path only) + < 120s budget assertion.

---

## Polish / cross-cutting

- Run `mypy --strict` on touched modules across all WPs (NFR-003).
- Maintain ≥ 90% line coverage on changed code (NFR-002).
- Each WP includes its own CHANGELOG entry contribution where called out; WP07 stitches the tranche summary.
- No new top-level dependencies (SC-008).

## MVP scope

If the tranche must ship in stages, the MVP is **WP01 + WP02** — restoring the fresh-project setup baseline and the strict-JSON contract. WP03–WP05 close production state-corruption bugs. WP06 + WP07 close the documented golden path. All seven are required to satisfy the spec's full acceptance set; staging is only relevant if the merge window forces it.

## Parallelization opportunities

- WP02, WP03, WP05 can all start simultaneously alongside WP01 (no dependencies).
- WP04 starts immediately after WP03.
- WP06 starts after WP01.
- WP07 is the capstone — runs once everything else is merged.
