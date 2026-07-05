# Tasks: Topology-Aware Legacy Warning (#2351)

**Mission**: `topology-aware-legacy-warning-01KWQ8WH`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

One cohesive work package: a warning-only topology classifier + message update in `transaction.py`, the coupled runbook edit, and the full test matrix. The shared `_is_legacy_mission()` predicate (routing + write-contract) is left untouched.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red: 7-case warning matrix + classifier unit + routing-invariance + backfill-suppression tests | WP01 | |
| T002 | Add `_warrants_legacy_warning` classifier (reuse `stored_topology_from_meta`) | WP01 | |
| T003 | Re-point the emit at `:730` to gate on the classifier; leave predicate/routing/write-contract untouched | WP01 | |
| T004 | Amend `_emit_legacy_warning_once` message to cite `spec-kitty migrate backfill-topology` | WP01 | |
| T005 | Update `legacy-to-coordination.md` (3 paragraphs) + terminology guard | WP01 | |
| T006 | Green: all tests + `mypy --strict` + `ruff` + terminology gate | WP01 | |

---

## WP01 — Topology-aware warning-only classifier + coupled runbook

- **Goal**: The legacy-topology warning no longer fires for `single_branch`/`lanes`/`flattened` missions but still fires (citing the runbook **and** `spec-kitty migrate backfill-topology`) for genuinely pre-SSOT legacy missions — with the shared routing/write-contract predicate provably unchanged.
- **Priority**: P1.
- **Independent test**: run the bookkeeping seam across the 7-shape matrix and assert warn/no-warn per shape; assert `single_branch`/`lanes` still take the legacy lane-worktree + `primary_checkout_append` path (routing unchanged).
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005.
- **Prompt**: [tasks/WP01-topology-aware-warning-classifier.md](./tasks/WP01-topology-aware-warning-classifier.md) (~280 lines)

### Subtasks

- [ ] T001 Red: extend `tests/integration/test_legacy_mission_fallback.py` (parametrize `_make_legacy_mission` with `topology=`/`flattened=`) for the 7 cases + add `tests/specify_cli/coordination/test_legacy_warning_classifier.py` unit tests + a routing/write-contract invariance test + a backfill-suppression test (WP01)
- [ ] T002 Add `_warrants_legacy_warning(repo_root, mission_slug, mid8) -> bool` in `transaction.py` reusing `stored_topology_from_meta` (function-local import); optional `_load_mission_meta` DRY hoist (WP01)
- [ ] T003 Wrap the emit at `transaction.py:730` with `_warrants_legacy_warning(...)`; leave `_is_legacy_mission` (`:200-230`), routing (`:719-729`), `_legacy_mode` (`:831`), write-contract (`:909`) untouched (WP01)
- [ ] T004 Amend the `_emit_legacy_warning_once` message (`:341-347`) to cite `spec-kitty migrate backfill-topology` alongside the runbook (message-only) (WP01)
- [ ] T005 Update `docs/migrations/legacy-to-coordination.md` (bullet `:61-65`, flattened bullet `:66-69`, Path A note `:125-127`) to match; run `tests/architectural/test_no_legacy_terminology.py` (WP01)
- [ ] T006 Make all tests green; `mypy --strict` + `ruff` zero-issue, no new suppressions; terminology gate passes (WP01)

### Dependencies

None (single WP).

---

## MVP

WP01 is the whole mission — a single, tightly-scoped bug fix with its coupled documentation.
