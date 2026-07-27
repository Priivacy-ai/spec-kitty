# Tasks: Untrusted-Path Containment Hardening

**Mission**: `untrusted-path-containment-hardening-01KVFTFV` | **Branch**: `automation/sonar-security-20260619` (rides PR #2036)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tasks translate the plan's Implementation Concern Map (IC-01…IC-05, IC-00 baseline)
into work packages, linearized per the plan's decomposition note to avoid
ownership overlap on the shared `status/` surface:
WP01 audit (read-only) → WP02 (status/+core seam fixes) & WP03 (other-package fixes) →
WP04 guard; WP05 (loopback) runs in parallel.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Define + commit the reproducible audit ruleset (seed-set + sink predicate) | WP01 | |
| T002 | Run the audit; enumerate every untrusted→FS sink in `src/specify_cli` | WP01 | |
| T003 | Classify each sink: routed-through-seam / unreachable / trusted-source | WP01 | |
| T004 | Emit the audit record; assert emitted count == inventory rows (completeness) | WP01 | |
| T005 | Document aggregate.py raise-guard + disposition its composed-path reads (FR-003) | WP01 | |
| T006 | store.py `_SlugResolver.resolve` `resolve()`-containment via `ensure_within_any` | WP02 | |
| T007 | store.py symlink-escape negative + symlinked-root positive tests (mutation-verified) | WP02 | |
| T008 | `mission_metadata.resolve_mission_identity` `safe_mission_slug` chokepoint (FR-009) | WP02 | |
| T009 | Negative test: hostile `meta.json` + empty event slug → no write outside `derived/` (views+lifecycle) | WP02 | |
| T010 | Route any WP01-flagged reachable `status/` sink through the seam | WP02 | |
| T011 | Gates: ruff/mypy/tests; confirm #2036 baseline not regressed (FR-007) | WP02 | |
| T012 | Disposition/fix `events/decision_log.py` mission_slug write sink | WP03 | [P] |
| T013 | Disposition/fix `coordination/surface_resolver.py` + `missions/_read_path_resolver.py` composed paths | WP03 | [P] |
| T014 | Disposition/fix `dossier/drift_detector.py` + `migration/mission_state.py` | WP03 | [P] |
| T015 | Disposition/fix `review/arbiter.py` + `post_merge/review_artifact_consistency.py` wp_id sinks; document `review/cycle.py` | WP03 | [P] |
| T016 | Negative tests for each confirmed-reachable WP03 fix | WP03 | |
| T017 | Gates for WP03 changes | WP03 | |
| T018 | Implement `tests/architectural/` guard reading the WP01 inventory; assert audited surfaces use the seam | WP04 | |
| T019 | Guard self-test: fixture join makes guard FAIL; removing guard makes fixture PASS (load-bearing) | WP04 | |
| T020 | Confirm guard runs in the architectural gate; full suite green | WP04 | |
| T021 | Add loopback-only rationale docstring/comments to `core/loopback_http.py` | WP05 | [P] |
| T022 | Retain/strengthen `tests/core/test_loopback_http.py` 127.0.0.1-binding regression tests | WP05 | [P] |
| T023 | Record the 2 Sonar hotspots (rule key + PR #2036) for UI review | WP05 | [P] |
| T024 | Gates for WP05 | WP05 | |

## Work Packages

### WP01 — Reproducible untrusted→FS sink audit (read-only inventory)

- **Goal**: Produce a re-runnable audit (recorded ruleset) enumerating every untrusted-segment→FS sink in `src/specify_cli`, each with one disposition (routed-through-seam / unreachable / trusted-source). No production-code changes. (IC-02; FR-004, FR-003)
- **Priority**: P1 (gates WP02/WP03/WP04). **Independent test**: re-running the committed ruleset reproduces the same inventory; every row has a disposition; emitted count == rows.
- **Subtasks**:
  - [x] T001 Define + commit the reproducible audit ruleset (WP01)
  - [x] T002 Run the audit; enumerate every untrusted→FS sink (WP01)
  - [x] T003 Classify each sink with a disposition + rationale (WP01)
  - [x] T004 Emit the audit record; assert count completeness (WP01)
  - [x] T005 Document aggregate.py raise-guard + disposition composed-path reads (WP01)
- **Dependencies**: none. **Est. size**: ~300 lines.
- **Prompt**: [tasks/WP01-untrusted-sink-audit.md](./tasks/WP01-untrusted-sink-audit.md)

### WP02 — status/ + meta.json seam fixes (IC-01 + IC-05)

- **Goal**: Add `resolve()`-containment to `store.py` resolver (FR-002) and route the `meta.json`-derived slug through `safe_mission_slug` at the single `mission_metadata` chokepoint (FR-009), closing the live write-path bypass in `views.py`/`lifecycle.py`; route any WP01-flagged reachable `status/` sink. Mutation-verified tests incl. the macOS symlinked-root positive case. (FR-002, FR-007, FR-008, FR-009, C-004)
- **Priority**: P1 (core fix). **Independent test**: hostile event-slug AND hostile `meta.json`-slug both fail closed (no read/write outside trusted roots); legitimate slug under a symlinked root accepted.
- **Subtasks**:
  - [x] T006 store.py resolve()-containment (WP02)
  - [x] T007 store.py symlink-escape + symlinked-root tests (WP02)
  - [x] T008 mission_metadata safe_mission_slug chokepoint (WP02)
  - [x] T009 hostile meta.json + empty event slug negative test (WP02)
  - [x] T010 route WP01-flagged reachable status/ sinks (WP02)
  - [x] T011 gates + no-regression of #2036 baseline (WP02)
- **Dependencies**: WP01. **Est. size**: ~450 lines.
- **Prompt**: [tasks/WP02-status-meta-seam-fixes.md](./tasks/WP02-status-meta-seam-fixes.md)

### WP03 — Other-package reachable sink fixes (audit-driven)

- **Goal**: For each WP01-confirmed-reachable sink outside `status/` (the pre-named candidates + any the ruleset surfaces), route it through the canonical seam; for unreachable/trusted ones, record the disposition. Negative tests for each fix. (FR-001, FR-003, FR-004, FR-008)
- **Priority**: P2. **Independent test**: each fixed sink rejects/falls-back on a traversal segment (negative test); unreachable sinks have a documented rationale.
- **Subtasks**:
  - [x] T012 events/decision_log.py (WP03)
  - [x] T013 coordination/surface_resolver.py + missions/_read_path_resolver.py (WP03)
  - [x] T014 dossier/drift_detector.py + migration/mission_state.py (WP03)
  - [x] T015 review/arbiter.py + post_merge wp_id sinks; document review/cycle.py (WP03)
  - [x] T016 negative tests for confirmed-reachable fixes (WP03)
  - [x] T017 gates (WP03)
- **Dependencies**: WP01. **Est. size**: ~480 lines.
- **Prompt**: [tasks/WP03-other-package-sink-fixes.md](./tasks/WP03-other-package-sink-fixes.md)

### WP04 — Load-bearing architectural regression guard (IC-03)

- **Goal**: A `tests/architectural/` guard, anchored on the WP01 inventory, that fails when a new unvalidated untrusted-segment join appears on an audited surface; proven load-bearing by a self-test. (FR-005, SC-006)
- **Priority**: P2 (after fixes land). **Independent test**: a fixture join makes the guard fail; removing the guard makes that fixture test pass.
- **Subtasks**:
  - [x] T018 implement the guard reading the inventory (WP04)
  - [x] T019 guard self-test (load-bearing) (WP04)
  - [x] T020 confirm gate placement; full suite green (WP04)
- **Dependencies**: WP01, WP02, WP03. **Est. size**: ~280 lines.
- **Prompt**: [tasks/WP04-architectural-regression-guard.md](./tasks/WP04-architectural-regression-guard.md)

### WP05 — loopback_http.py rationale + hotspot record (IC-04)

- **Goal**: Document the loopback-only (127.0.0.1) rationale in-code, retain the binding regression tests, and record the two Sonar hotspots for UI review. No behavioural change; no HTTPS forcing. (FR-006, C-001)
- **Priority**: P3 (independent, parallel). **Independent test**: regression tests still assert 127.0.0.1 binding; rationale present; hotspot record cites rule key + PR #2036.
- **Subtasks**:
  - [x] T021 loopback rationale docstring/comments (WP05)
  - [x] T022 retain/strengthen binding regression tests (WP05)
  - [x] T023 record the 2 Sonar hotspots (WP05)
  - [x] T024 gates (WP05)
- **Dependencies**: none (parallel). **Est. size**: ~220 lines.
- **Prompt**: [tasks/WP05-loopback-rationale-hotspot.md](./tasks/WP05-loopback-rationale-hotspot.md)

## Dependency Graph

```
WP01 (audit) ──┬──▶ WP02 (status/meta fixes) ──┐
               └──▶ WP03 (other-pkg fixes)  ────┼──▶ WP04 (guard)
WP05 (loopback) ───────────────────────────────┘ (independent, parallel)
```

## MVP / Sequencing

- **MVP**: WP01 → WP02 (closes the highest-severity live write-path traversal via FR-009 + the store.py read residual).
- WP03 broadens coverage to the rest of the CLI; WP04 locks it against regression; WP05 is independent documentation hardening.
