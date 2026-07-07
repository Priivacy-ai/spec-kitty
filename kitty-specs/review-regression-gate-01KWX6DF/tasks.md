# Work Packages: Auto-scoped review-time regression gate

**Mission**: `review-regression-gate-01KWX6DF` | **Issues**: Closes #572 + #1979 (blind-spot facet); Part of #2283 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Two WPs: WP01 = the scope-derivation + head-side runner + verdict engine (`review/pre_review_gate.py` + the arch invariant); WP02 = the `for_review` gate hook + config/override precedence. WP02 depends on WP01 (needs the verdict).

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Affected-scope derivation keyed on group shape: per-shard groups' `tests/**` globs (via `aggregate_filter_groups()`) + composite groups' census `_COMPOSITE_ROUTING` cone_roots; EXCLUDE catch-alls (`core_misc`/`e2e`/`any_src`) | WP01 | FR-002, FR-005 |
| T002 | Head-side scoped runner: invoke the affected shards at head, parse JUnit (reuse `baseline.py`), compute new-failures = head − base via `diff_baseline`; degrade to warn if baseline uncomputable | WP01 | FR-003 |
| T003 | FR-006 arch invariant: derivation reads the live authorities for BOTH shapes + the exclusion (fails on a stale/hand-authored map) | WP01 | FR-006 |
| T004 | Gate hook at `move-task --to for_review`: warn-default, opt-in block (`review.fail_on_pre_review_regression`), `--force` recorded in evidence | WP02 | FR-001, NFR-001 |
| T005 | Override precedence: frontmatter `pre_review_test_scope` > config `review.pre_review_test_command` > census-derived default | WP02 | FR-004 |
| T006 | Integration + non-vacuity: a WP that breaks a consuming shard is surfaced/blocked; a pre-existing base red does NOT block (baseline diff); bounded scope asserted (status/emit.py → status shard, not core_misc) | WP02 | FR-001, FR-005, SC-001, SC-002 |

---

## Work Package WP01: Scope-derivation + head-side runner + verdict engine (Priority: P1)
**Prompt**: `/tasks/WP01-scope-runner-verdict.md`
**Goal**: `review/pre_review_gate.py` derives the affected test set (two group shapes, catch-alls excluded), runs it at head, and computes the new-failure verdict — reusing `baseline.py`'s JUnit parser + `diff_baseline`; the FR-006 arch invariant guards the derivation.
### Included Subtasks
- [x] T001 Group-shape scope derivation + catch-all exclusion (WP01)
- [x] T002 Head-side scoped runner + new-failure verdict (WP01)
- [x] T003 FR-006 single-source invariant (both shapes) (WP01)
### Dependencies
None.
### Risks & Mitigations
- Composite dirs silently under-covered → FR-006 invariant asserts BOTH shapes (per-shard globs + composite cone_roots).
- Catch-all cost explosion → the `core_misc`/`e2e`/`any_src` exclusion + surfaced affected count.

## Work Package WP02: `for_review` gate hook + config/override precedence (Priority: P1)
**Prompt**: `/tasks/WP02-gate-hook-config.md`
**Goal**: wire WP01's verdict into `move-task --to for_review` — warn-default, opt-in block, `--force`, override precedence — with an integration + non-vacuity proof.
### Included Subtasks
- [ ] T004 Gate hook (warn/block/--force) (WP02)
- [ ] T005 Override precedence (WP02)
- [ ] T006 Integration + non-vacuity + bounded-scope proof (WP02)
### Dependencies
WP01 (needs the verdict engine).
### Risks & Mitigations
- Blocking what should warn → warn-default (NFR-001) + `--force`.
- Baseline uncomputable → degrade to warn, never hard-block (FR-003 edge).
