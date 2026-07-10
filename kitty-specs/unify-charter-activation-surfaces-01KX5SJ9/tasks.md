# Tasks: Unify charter activation surfaces

**Mission**: unify-charter-activation-surfaces-01KX5SJ9 | **Branch**: `epic/2519-charter-authoring-lifecycle` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Make `config.activated_*` the single activation authority; the compiled reference set + graph derive from it; `answers.selected_*` retired as an activation source; fail-closed parity guard; shared append-promotion primitive for the migration + interview. IC-01 foundation first.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Stem→canonical resolver over config.activated_* (reuse/harden resolve_config_id) | WP01 | |
| T002 | Reject-not-drop on a malformed/unresolvable stem | WP01 | |
| T003 | 25-directive stem↔canonical parity fixture | WP01 | |
| T004 | Non-vacuity test: a malformed stem is rejected, not silently dropped | WP01 | |
| T005 | compiler `_build_references` reads config.activated_* (via WP01 resolver) | WP02 | |
| T006 | compiler charter.md render sources selections from config | WP02 | |
| T007 | `_synthesis.py` interview_snapshot/drg_snapshot sourced from config (2nd derivation path) | WP02 | |
| T008 | `generate.py` compile path wired to config-sourced derivation | WP02 | |
| T009 | Tests: compiler + synthesis produce the config-sourced set | WP02 | |
| T010 | Regenerate `.kittify/charter/references.yaml` from config (superset: +paradigms +direct styleguides/toolguides) | WP03 | |
| T011 | Regenerate `src/doctrine/graph.yaml`; freshness gate green | WP03 | |
| T012 | Shrink `test_dangling_baseline_is_shrink_only` to empty; fix dangler-test helper call shape | WP03 | |
| T013 | Regression: `charter activate` → resolves with no answers edit (the #2524 class) | WP03 | |
| T014 | Union org_charter `apply_org_charter_to_interview` required_* into config.activated_* | WP04 | [P] |
| T015 | SC-004 test: editing answers.selected_* without config has no effect on the compiled set | WP04 | [P] |
| T016 | Confirm third-ledger (governance.yaml) + spdd_reasons/activation.py untouched; resolver.py:372 staleness noted | WP04 | [P] |
| T017 | Parity: assert config↔references at ID level (the #2524 dangler class) | WP05 | [P] |
| T018 | Parity: assert config↔graph at KIND level (do NOT build the punted ID map) | WP05 | [P] |
| T019 | Doctrine-test-tier entry point for the guard (currently CLI-only) | WP05 | [P] |
| T020 | Non-vacuity self-test: a planted config↔derived divergence bites; disjoint from freshness | WP05 | [P] |
| T021 | New append/set primitive in activation_engine (promote roots; no default-pack pollution; first-run ordering) | WP06 | |
| T022 | Primitive tests: append semantics, paradigm promotion, layer-rule green | WP06 | |
| T023 | Migration: config-seeded, zero-drop, promotes answers-only paradigms (calls WP06 primitive) | WP07 | [P] |
| T024 | Interview wiring (FR-007 append-promotion of captured selections; calls WP06 primitive) | WP07 | [P] |
| T025 | Migration fixture (constructed synthetic reverse-skew) + defer-deselect follow-up note | WP07 | [P] |
| T026 | Direct-root inclusion: read config.activated_styleguides/toolguides (+direct kinds) as roots (squad LAND-BLOCKER) | WP02 | |
| T027 | Deactivate-drops regression (Scenario 2) + SPDD-no-flip assertion | WP03 | |
| T028 | Re-pin 6 stale answers-sourced charter tests to config-sourced (out-of-map, rationale-backed) | WP03 | |

## Work Packages

### WP01 — ID-form parity foundation (stem↔canonical)

- **Goal**: The #1 correctness guard (C-006). A charter-package resolver that maps `config.activated_*` slug-stems → canonical artefact ids exactly as the live `DoctrineService`/DRG does, **rejecting** (never silently dropping) a malformed stem. Foundation for both the derivation switch (WP02) and the promotion primitive (WP06).
- **Priority**: P0 (MVP foundation) · **Dependencies**: none
- **Requirements**: FR-001, C-006 · **Independent test**: 25-directive stem↔canonical parity fixture + malformed-stem-rejected non-vacuity test green.
- **Prompt**: [tasks/WP01-id-parity-foundation.md](tasks/WP01-id-parity-foundation.md) (~4 subtasks)

- [x] T001 Stem→canonical resolver over config.activated_* (reuse/harden `charter.kind_vocabulary.resolve_config_id`) (WP01)
- [x] T002 Reject-not-drop on a malformed/unresolvable stem (WP01)
- [x] T003 25-directive stem↔canonical parity fixture (WP01)
- [x] T004 Non-vacuity test: a malformed stem is rejected, not silently dropped (WP01)

### WP02 — IC-01 derivation source switch (both paths)

- **Goal**: Repoint the compiled reference set + graph derivation from `answers.selected_*` to `config.activated_*` in BOTH `charter/compiler.py` (references) AND `specify_cli/.../_synthesis.py` (graph layer) + `generate.py`, via the WP01 resolver.
- **Priority**: P0 · **Dependencies**: WP01
- **Requirements**: FR-001, FR-002, C-005, C-006 · **Independent test**: compiler + synthesis emit the config-sourced set (incl. directly-activated styleguides/toolguides); an unresolvable stem raises; unit tests green.
- **Prompt**: [tasks/WP02-derivation-source-switch.md](tasks/WP02-derivation-source-switch.md) (~6 subtasks)

- [x] T005 compiler `_build_references` reads config.activated_* (via WP01 resolver) (WP02)
- [x] T006 compiler charter.md render sources selections from config (WP02)
- [x] T007 `_synthesis.py` interview_snapshot/drg_snapshot sourced from config (2nd derivation path) (WP02)
- [x] T008 `generate.py` compile path wired to config-sourced derivation (WP02)
- [x] T009 Tests: compiler + synthesis produce the config-sourced set; unresolvable stem raises (WP02)
- [x] T026 Direct-root inclusion for config-activated styleguides/toolguides (+direct kinds) so non-directive-reachable artefacts resolve (WP02)

### WP03 — IC-01 consequence: regenerate committed artefacts + baseline shrink

- **Goal**: The config-sourced switch is a SUPERSET (adds paradigms + direct styleguides/toolguides), so the committed `references.yaml` + `graph.yaml` change content and must be regenerated + re-committed, the shrink-only dangler baseline shrunk to empty, and the #2524 regression pinned (C-008).
- **Priority**: P0 · **Dependencies**: WP02
- **Requirements**: FR-004, C-003, C-008, SC-001 · **Independent test**: `activate` → resolves with no answers edit; freshness gate green; baseline empty.
- **Prompt**: [tasks/WP03-regenerate-artefacts-baseline.md](tasks/WP03-regenerate-artefacts-baseline.md) (~5 subtasks)

- [x] T010 Regenerate `.kittify/charter/references.yaml` from config (superset) (WP03)
- [x] T011 Regenerate `src/doctrine/graph.yaml`; freshness gate green (WP03)
- [x] T012 Shrink `test_dangling_baseline_is_shrink_only` to empty; fix dangler-test helper call shape (WP03)
- [x] T013 Regression: `charter activate` → resolves with no answers edit (the #2524 class) (WP03)
- [x] T027 Deactivate-drops regression (Scenario 2) + SPDD-no-flip assertion (WP03)
- [x] T028 Re-pin 6 stale answers-sourced charter tests to config-sourced (out-of-map, rationale-backed) (WP03)

### WP04 — IC-02 retire answers + org-feeder union

- **Goal**: Make `answers.selected_*` inert for activation and prevent the org-feeder break — union `org_charter.apply_org_charter_to_interview` required_* into `config.activated_*`; keep the third ledger (governance.yaml) + `spdd_reasons/activation.py` untouched (C-007).
- **Priority**: P1 · **Dependencies**: WP02, WP03, WP06 · **Parallel with**: WP05
- **Requirements**: FR-003, C-007, SC-004 · **Independent test**: editing answers without config has no effect on the compiled set; org-required artefacts still resolve.
- **Prompt**: [tasks/WP04-retire-answers-org-union.md](tasks/WP04-retire-answers-org-union.md) (~3 subtasks)

- [ ] T014 Union org_charter `apply_org_charter_to_interview` required_* into config.activated_* (WP04)
- [ ] T015 SC-004 test: editing answers.selected_* without config has no effect on the compiled set (WP04)
- [ ] T016 Confirm third-ledger (governance.yaml) + spdd_reasons/activation.py untouched; resolver.py:372 staleness noted (WP04)

### WP05 — IC-03 fail-closed parity guard

- **Goal**: Extend `charter/consistency_check.py` to assert config↔references at ID level (the #2524 dangler class) + config↔graph at KIND level, fail-closed, with a doctrine-test-tier entry point and a non-vacuity self-test. DISJOINT from `freshness/computer.py` (no import/reference — layer rule).
- **Priority**: P1 · **Dependencies**: WP02, WP03 · **Parallel with**: WP04
- **Requirements**: FR-005, NFR-002 · **Independent test**: a planted divergence fails the guard in the doctrine suite.
- **Prompt**: [tasks/WP05-parity-guard.md](tasks/WP05-parity-guard.md) (~4 subtasks)

- [ ] T017 Parity: assert config↔references at ID level (the #2524 dangler class) (WP05)
- [ ] T018 Parity: assert config↔graph at KIND level (do NOT build the punted ID map) (WP05)
- [ ] T019 Doctrine-test-tier entry point for the guard (currently CLI-only) (WP05)
- [ ] T020 Non-vacuity self-test: a planted config↔derived divergence bites; disjoint from freshness (WP05)

### WP06 — Append-promotion primitive (activation_engine)

- **Goal**: A NEW append/set primitive in `charter/activation_engine.py` that promotes answers-roots {directives ∪ paradigms} into `config.activated_*` (via `commit_plan`), handling first-run ordering (no default-pack pollution) and paradigm promotion. The indivisible core shared by the migration (WP07) and interview (WP07). Layer-legal (charter only).
- **Priority**: P1 · **Dependencies**: WP01 · **Parallel with**: WP02
- **Requirements**: FR-006, FR-007, C-001, C-002 · **Independent test**: primitive promotes a directive+paradigm root set append-only without materializing the default pack.
- **Prompt**: [tasks/WP06-append-promotion-primitive.md](tasks/WP06-append-promotion-primitive.md) (~3 subtasks)

- [x] T021 New append/set primitive in activation_engine (promote roots; no default-pack pollution; first-run ordering) (WP06)
- [x] T022 Primitive tests: append semantics, paradigm promotion, layer-rule green (WP06)

### WP07 — Promotion consumers: migration + interview wiring (FR-007)

- **Goal**: Wire BOTH consumers of the WP06 primitive — the config-seeded, zero-drop migration (promotes answers-only paradigms) AND the interview command (FR-007 append-promotion of captured selections). DEFER only the re-interview replace/deselect refinement to a tracked follow-up.
- **Priority**: P1 · **Dependencies**: WP06
- **Requirements**: FR-006, FR-007 · **Independent test**: a skewed fixture project migrates with 0 drop incl. answers-only paradigm; a fresh interview activates its selections into config.
- **Prompt**: [tasks/WP07-promotion-consumers.md](tasks/WP07-promotion-consumers.md) (~3 subtasks)

- [x] T023 Migration: config-seeded, zero-drop, promotes answers-only paradigms (calls WP06 primitive) (WP07)
- [x] T024 Interview wiring (FR-007 append-promotion of captured selections; calls WP06 primitive) (WP07)
- [x] T025 Migration fixture (25-vs-24 skew + answers-only paradigm) + defer-deselect follow-up note (WP07)

## Dependency Graph

```
WP01 (ID-parity foundation)
 ├──> WP02 (derivation switch) ──> WP03 (regen + baseline) ──┬─> WP04 (retire answers + org-union) ∥ WP05 (parity guard)
 └──> WP06 (promotion primitive) ───────────────────────────┴─> WP07 (migration + interview wiring)
       [WP02 ∥ WP06 after WP01]  ·  WP04 also depends on WP06 (consumes the arbitrary-kind promotion primitive)
```

## MVP & Parallelization

- **MVP**: WP01 → WP02 → WP03 (the authority switch + the #2524 fix). WP04/WP05 (retire + guard) and WP06/WP07 (promotion) complete the slice.
- **Parallel**: WP02 ∥ WP06 (after WP01); WP04 ∥ WP05 (after WP03).
- **Closeout gate** (in WP05, last correctness WP): full `tests/doctrine/` + `tests/charter/` + `test_layer_rules.py` + graph freshness + terminology guard + ruff/mypy.
- **Deferred follow-up** (filed at close): the re-interview *replace/deselect* refinement (does re-interview deactivate dropped selections?) — append-only promotion ships in this slice.
