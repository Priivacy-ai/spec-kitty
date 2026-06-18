# Tasks: Governed-State-Surface Coherence

**Mission:** governed-state-surface-coherence-01KVCGQC (mid8 01KVCGQC)
**Branch:** `feat/governed-state-surface-coherence` → PR → `main`
**Plan:** [plan.md](./plan.md) · **Research:** [research.md](./research.md)

## Dependency DAG

```
WP01 (IC-D, green main) ──┬──> WP02 (IC-A, #2016 coord-read)
                          ├──> WP03 (IC-B1, charter status JSON + pins)
                          ├──> WP04 (IC-B2, charter freshness residue + unlink)
                          └──> WP05 (IC-C, merge baseline extract)
```

WP01 has no dependencies and greens the architectural gate; WP02–WP05 each depend only on WP01 and are mutually independent (disjoint `owned_files`) → 4 parallel lanes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Add `git_repo` marker, drop `fast` on test_read_path_resolver_validation.py (D1) | WP01 | |
| T002 | Remove mission-diff-scoped test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils (D2) | WP01 | |
| T003 | Reconcile the 3 re-keyed ratchet baselines to current main tree (D3) | WP01 | |
| T004 | Verify the architectural shard GREEN under real CI conditions (NFR-003) | WP01 | |
| T010 | Failing-first test: coord-only-no-primary-meta topology returns coord dir (#2016) | WP02 | |
| T011 | Adopt the canonical `_coord_mid8` cascade in `_resolve_mission_dir` (consolidate; no second resolver) | WP02 | |
| T012 | Preserve `StatusReadPathNotFound` fail-closed for no-tail+no-declared-id | WP02 | |
| T013 | Fold: retype `_fail -> NoReturn`; delete the two `raise # unreachable` lines (S5747) | WP02 | |
| T014 | mypy/ruff clean ≤15; full #2016 regression class green | WP02 | |
| T020 | Failing-first test: `charter status --json` on metadata.yaml with unquoted `timestamp_utc` datetime (C2-b) | WP03 | |
| T021 | JSON-safe serialization of the status payload, string-typed (FR-005) | WP03 | |
| T022 | Pin C2-a: status read path invokes no mutator (FR-008a) | WP03 | |
| T030 | Failing-first test: built_in_only ∧ stray graph.yaml blocks preflight today (C2-f) | WP04 | |
| T031 | Downgrade `invalid` → `built_in_only` + residue diagnostic; update test_computer; genuine-`invalid` guard (FR-006) | WP04 | |
| T032 | One `unlink_stale_project_graph` helper in graph_residue.py; wire both callers, atomic-safe (FR-007) | WP04 | |
| T033 | Live-repro C2-e (sync noop-despite-stale); fix-or-document-with-evidence (FR-009) | WP04 | |
| T034 | mypy/ruff clean ≤15 (ruff C901); preflight/freshness suites green | WP04 | |
| T035 | Pin C2-d: real surfaces (sync/status/computer) agree via one `hash_content` (FR-008b) | WP04 | |
| T040 | Relocate the 5 baseline functions verbatim → `merge/baseline.py` (FR-010) | WP05 | |
| T041 | Re-export the 3 public names via `merge/__init__.py`; redirect merge.py's 2 call sites | WP05 | |
| T042 | Hoist `META_JSON = "meta.json"` for the moved occurrences (S1192) | WP05 | |
| T043 | Verify all baseline test suites pass unchanged; mypy/ruff clean | WP05 | |

---

## WP01 — Green main: repair the un-masked architectural gate (IC-D)

**Goal:** restore a GREEN `tests/architectural/**` shard on the mission branch so WP02–WP05 land on a green base.
**Priority:** P0 (MVP / blocks the lane). **Dependencies:** none.
**Independent test:** the architectural shard passes under CI conditions (py3.12 + installed + parallel).
**Tickets:** #2025 · **Prompt:** [tasks/WP01-green-main-architectural-gate.md](./tasks/WP01-green-main-architectural-gate.md)

- [x] T001 Add `git_repo` marker, drop `fast` on test_read_path_resolver_validation.py (WP01)
- [x] T002 Remove mission-diff-scoped test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils (WP01)
- [x] T003 Reconcile the 3 re-keyed ratchet baselines to the current main tree (WP01)
- [x] T004 Verify the architectural shard GREEN under real CI conditions (WP01)

## WP02 — #2016 orchestrator coord-read adoption (IC-A)

**Goal:** `_resolve_mission_dir` resolves coord-only-with-tail-slug missions via the canonical `_coord_mid8` cascade; fail-closed preserved.
**Priority:** P1. **Dependencies:** WP01.
**Independent test:** `test_coord_path_returned_when_coord_exists` green; `test_none_returned_when_mission_not_found` still green.
**Tickets:** #2016 · **Prompt:** [tasks/WP02-coord-read-adoption.md](./tasks/WP02-coord-read-adoption.md)

- [x] T010 Failing-first test: coord-only-no-primary-meta topology returns coord dir (WP02)
- [x] T011 Adopt the canonical `_coord_mid8` cascade in `_resolve_mission_dir` (WP02)
- [x] T012 Preserve `StatusReadPathNotFound` fail-closed for no-tail+no-declared-id (WP02)
- [x] T013 Fold: retype `_fail -> NoReturn`; delete the two unreachable raises (WP02)
- [x] T014 mypy/ruff clean ≤15; full #2016 regression class green (WP02)

## WP03 — Charter status JSON-safe + landed-fix pins (IC-B1)

**Goal:** `charter status --json` never crashes on non-JSON-safe values; the already-landed C2-a/C2-d fixes are pinned against re-drift.
**Priority:** P1. **Dependencies:** WP01.
**Independent test:** `charter status --json` returns valid JSON on a datetime-bearing metadata.yaml; pin tests green.
**Tickets:** #2009 · **Prompt:** [tasks/WP03-charter-status-json-safe.md](./tasks/WP03-charter-status-json-safe.md)

- [x] T020 Failing-first test: `charter status --json` on metadata.yaml with unquoted `timestamp_utc` datetime (WP03)
- [x] T021 JSON-safe serialization of the status payload, string-typed (WP03)
- [x] T022 Pin C2-a: status read path invokes no mutator (WP03)

## WP04 — Charter freshness residue downgrade + unlink consolidation (IC-B2)

**Goal:** `built_in_only ∧ stray graph.yaml` becomes a non-blocking read-time residue (not terminal `invalid`); the two unlink sites consolidate to one helper; C2-e reproduced-or-documented.
**Priority:** P1. **Dependencies:** WP01.
**Independent test:** preflight PASSES on a residue fixture reporting `built_in_only` + diagnostic; one unlink helper has two callers.
**Tickets:** #2009 · **Prompt:** [tasks/WP04-charter-freshness-residue.md](./tasks/WP04-charter-freshness-residue.md)

- [x] T030 Failing-first test: built_in_only ∧ stray graph.yaml blocks preflight today (WP04)
- [x] T031 Downgrade `invalid` → `built_in_only` + residue diagnostic; update test_computer; genuine-`invalid` guard (WP04)
- [x] T032 One `unlink_stale_project_graph` helper in graph_residue.py; wire both callers, atomic-safe (WP04)
- [x] T033 Live-repro C2-e (sync noop-despite-stale); fix-or-document-with-evidence (WP04)
- [x] T034 mypy/ruff clean ≤15 (ruff C901); preflight/freshness suites green (WP04)
- [x] T035 Pin C2-d: real surfaces agree via one `hash_content` (WP04)

## WP05 — merge.py baseline extract (IC-C)

**Goal:** relocate the `baseline_merge_commit` cluster to `merge/baseline.py`, behavior-preserving, with back-compat re-exports.
**Priority:** P2. **Dependencies:** WP01.
**Independent test:** the 9+ baseline test suites pass unchanged; names importable from both `specify_cli.merge` and the legacy surface.
**Tickets:** #2027 (epic #2026) · **Prompt:** [tasks/WP05-merge-baseline-extract.md](./tasks/WP05-merge-baseline-extract.md)

- [x] T040 Relocate the 5 baseline functions verbatim → `merge/baseline.py` (WP05)
- [x] T041 Re-export the 3 public names via `merge/__init__.py`; redirect merge.py's 2 call sites (WP05)
- [x] T042 Hoist `META_JSON = "meta.json"` for the moved occurrences (WP05)
- [x] T043 Verify all baseline test suites pass unchanged; mypy/ruff clean (WP05)
