# Tasks: CI Scoping Gate Reliability

**Mission**: `ci-scoping-gate-reliability-01KZP80D` | **Branch**: `fix/ci-scoping-gate-reliability`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Authoritative squad remediation**: [tracer-squad-findings.md](./tracer-squad-findings.md) — B1/M1-M5/N1-N2 are binding.

Two independent work packages, one per blocking CI gate. They touch disjoint files
(`ci-quality.yml` + arch guards vs `docs-freshness.yml` + docs scripts/tests), so they run as
two parallel lanes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Discrete corpus globs in `ci-quality.yml` `pull_request.paths` **and** `push.paths` (B1, no braces) | WP01 | |
| T002 | `corpus` change-group: `changes.outputs.corpus` row + `corpus:` dorny filter (narrow globs) | WP01 | |
| T003 | `fast-tests-corpus` blocking job (modeled on `fast-tests-docs`, `-m corpus`, not whole dirs) | WP01 | |
| T004 | Wire the gate: `JOB_GROUPS["fast-tests-corpus"]=["corpus"]` + `quality-gate.needs` edge | WP01 | |
| T005 | Register `corpus` marker in `pytest.ini` + apply module-level `pytestmark` to corpus readers | WP01 | |
| T006 | Co-evolve `test_ci_quality_path_filters.py` + `test_ci_collection_completeness.py` | WP01 | |
| T007 | Corpus-trigger completeness invariant (M4): every corpus-read path matched by the globs | WP01 | |
| T008 | Diff-scope mode in `relative_link_fixer.py` (fail-closed base-ref, M5) | WP02 | [P] |
| T009 | Diff-scope mode in `related_validator.py --strict` (same fail-closed base-ref, M5) | WP02 | [P] |
| T010 | `docs-freshness.yml`: PR runs diff-scoped from `base.sha`; retain unfiltered `push:main` backstop | WP02 | |
| T011 | Co-evolve `test_docs_freshness_invariant.py` (keep backstop + PR-allowlist shape) | WP02 | |
| T012 | Co-evolve `test_rulers_blocking.py` (pass base/changed-set; seeded-violation RED stays green) | WP02 | |

The `[P]` marker indicates parallelism, not status. Record completion with
`spec-kitty agent tasks mark-status <Txxx> --status done`.

---

## WP01 — Corpus data triggers and gates the blocking corpus suite (#3008)

**Prompt**: [tasks/WP01-corpus-gate-trigger-and-blocking-job.md](./tasks/WP01-corpus-gate-trigger-and-blocking-job.md)
**Priority**: P1 (US1 + US2) | **Dependencies**: none | **Requirements**: FR-001, FR-002, FR-003,
NFR-001, NFR-002, NFR-003, NFR-004, C-001, C-003 | **Estimated prompt size**: ~420 lines

**Goal**: A data-only PR (`packs/**`, narrow `kitty-specs` planning files, `.kittify` corpus config)
triggers the quality workflow (closes Gate 0) and runs the corpus-reading suites as a **blocking**
job feeding `quality-gate` (closes Gate 1) — without firing on `status.events.jsonl`/notes/trace
churn and without double-running whole already-covered directories.

**Independent test**: Path-filter tests prove a `packs/built-in/**`-only diff selects the `corpus`
group and the `fast-tests-corpus` job; a `kitty-specs/<m>/status.events.jsonl`-only diff does NOT.

**Included subtasks**: T001, T002, T003, T004, T005, T006, T007

**Implementation sketch**:
1. Extend the two trigger allowlists with discrete corpus globs (B1).
2. Register the `corpus` change-group exactly like the `docs` precedent (M2) — five atomic edits.
3. Add the `fast-tests-corpus` blocking job (`-m corpus`, M1) and wire it into `quality-gate`.
4. Mark the corpus-reading modules and co-evolve the arch invariants + a new completeness guard.

**Risks**: brace-glob inertness (B1); double-run of whole dirs (M1 — bound with the marker);
touching `ci_topology_census.json`/`src_backed_groups`/the unmatched loop reds
`test_ci_topology_worklist` (M2); a missing `quality-gate.needs` edge reds
`test_suite_jobs_gate_blocking.py` (N2).

---

## WP02 — Docs dead-link gate is scoped to the PR's own diff (#3147)

**Prompt**: [tasks/WP02-docs-deadlink-diff-scope.md](./tasks/WP02-docs-deadlink-diff-scope.md)
**Priority**: P2 (US3) | **Dependencies**: none | **Requirements**: FR-004, FR-005, C-002
| **Estimated prompt size**: ~320 lines

**Goal**: Scope the two blocking whole-tree dead-link checks (`relative_link_fixer.py --check`,
`related_validator.py --strict`) to the PR's changed files, so unrelated pre-existing broken links
no longer fail a docs PR — while the unfiltered `push:main` whole-tree run is retained as the
non-blocking rot backstop (FR-005). The check still BITES on a link the PR itself breaks.

**Independent test**: A docs PR whose own diff has no broken links passes even when an untouched file
elsewhere has one; introduce a broken link in a changed file → it FAILS; the `push:main` scan still
reports the untouched link.

**Included subtasks**: T008, T009, T010, T011, T012

**Implementation sketch**:
1. Add a fail-closed diff-scope mode to both scripts (base-ref → changed docs files; empty set errors).
2. Update `docs-freshness.yml` to run the two gates diff-scoped on `pull_request` (from `base.sha`,
   `fetch-depth: 0`) while leaving the unfiltered `push:main` whole-tree run intact.
3. Co-evolve the two docs invariants.

**Risks**: false-green if the base-ref/changed-set is empty and the check passes trivially — MUST
fail-closed (M5); docs-freshness is NOT a required check — do not wire it into `quality-gate.needs`
(N1); the `push:main` backstop must survive (M3/C-002).

---

## MVP scope

WP01 (#3008) is the MVP: it closes a genuine correctness hole in the release gate (corpus regressions
shipping invisibly). WP02 (#3147) removes per-PR friction and is lower-stakes (rot is still caught by
the retained whole-tree scan).
